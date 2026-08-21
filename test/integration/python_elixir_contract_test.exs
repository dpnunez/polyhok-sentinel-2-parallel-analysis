defmodule PolyhokSentinel2ParallelAnalysis.Sentinel2.PythonElixirContractTest do
  use ExUnit.Case, async: false

  alias PolyhokSentinel2ParallelAnalysis.Sentinel2.Preparation
  alias PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparationRegistry
  alias PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparedReader

  @python Path.expand("python/.venv/bin/python")

  test "reads finite values and shared NaN positions written by Python" do
    root = fixture_root()
    writer = write_script(root, "small_writer.py", small_writer())
    assert {"", 0} = System.cmd(@python, [writer, root])

    metadata = %{
      "width" => 2,
      "height" => 2,
      "path_b04" => "contract/b04.f32",
      "path_b08" => "contract/b08.f32"
    }

    assert {:ok, %{b04: b04, b08: b08}} = PreparedReader.read_crop(root, metadata)
    assert Nx.type(b04) == {:f, 32}
    assert Nx.shape(b04) == {2, 2}
    assert Nx.to_flat_list(b04) == [0.125, :nan, 0.25, 0.375]
    assert Nx.to_flat_list(b08) == [0.5, :nan, 0.75, 0.875]
  end

  test "classifies nonzero, timeout, zero-invalid and zero-valid process outcomes" do
    root = fixture_root()

    assert {:error, {:process_failed, 6, ""}} =
             prepare(root, "nonzero", write_script(root, "nonzero.py", "raise SystemExit(6)\n"))

    assert {:error, :timeout} =
             prepare(
               root,
               "timeout",
               write_script(root, "timeout.py", "import time\ntime.sleep(2)\n"),
               timeout: 20
             )

    assert {:error, {:unreadable_file, "manifest.json", :enoent}} =
             prepare(root, "invalid", write_script(root, "invalid.py", "pass\n"))

    publisher = write_script(root, "publisher.py", contract_publisher())
    assert {:ok, prepared} = prepare(root, "valid", publisher)
    assert prepared.scene_id == "valid"
    assert Enum.map(prepared.crops, & &1["width"]) == [1024, 4096, 8192]
  end

  test "keeps an interrupted scene unpublished and preserves all binary mtimes on reuse" do
    root = fixture_root()
    interrupted = write_script(root, "interrupted.py", interrupted_writer())

    assert {:error, {:process_failed, 8, ""}} = prepare(root, "reuse", interrupted)
    refute File.exists?(Path.join(root, "fixtures/sentinel-2/manifest.json"))

    publisher = write_script(root, "publisher.py", contract_publisher())
    assert {:ok, _prepared} = prepare(root, "reuse", publisher)
    binaries = prepared_binaries(root, "reuse")
    before = Map.new(binaries, &{&1, File.stat!(&1, time: :posix).mtime})

    Process.sleep(1_100)
    assert {:ok, _prepared} = prepare(root, "reuse", publisher)
    after_reuse = Map.new(binaries, &{&1, File.stat!(&1, time: :posix).mtime})

    assert after_reuse == before
  end

  test "allows one active cross-process request and rejects its duplicate" do
    root = fixture_root()

    sleeper =
      write_script(root, "sleeper.py", "import time\ntime.sleep(0.2)\nraise SystemExit(1)\n")

    options = options(root, sleeper)
    scene = %{scene_id: "concurrent", safe_path: Path.join(root, "concurrent.SAFE")}
    first = Task.async(fn -> Preparation.prepare(scene, options) end)
    assert_registered("concurrent")

    assert {:error, :already_running} = Preparation.prepare(scene, options)
    assert {:error, {:process_failed, 1, ""}} = Task.await(first, 1_000)
  end

  defp prepare(root, scene_id, entrypoint, extra \\ []) do
    scene = %{scene_id: scene_id, safe_path: Path.join(root, "#{scene_id}.SAFE")}
    Preparation.prepare(scene, options(root, entrypoint, extra))
  end

  defp options(root, entrypoint, extra \\ []) do
    [project_root: root, executable: @python, entrypoint: entrypoint, timeout: 5_000]
    |> Keyword.merge(extra)
  end

  defp prepared_binaries(root, scene_id) do
    for size <- [1024, 4096, 8192], band <- ["b04", "b08"] do
      Path.join(
        root,
        "fixtures/sentinel-2/scenes/#{scene_id}/prepared/#{size}x#{size}/#{band}.f32"
      )
    end
  end

  defp fixture_root do
    path = Path.join(System.tmp_dir!(), "python-elixir-#{System.unique_integer([:positive])}")
    File.mkdir_p!(path)
    on_exit(fn -> File.rm_rf!(path) end)
    path
  end

  defp write_script(root, name, body) do
    path = Path.join(root, name)
    File.write!(path, body)
    path
  end

  defp assert_registered(scene_id, attempts \\ 50)

  defp assert_registered(scene_id, attempts) when attempts > 0 do
    case Registry.lookup(PreparationRegistry, scene_id) do
      [] ->
        Process.sleep(5)
        assert_registered(scene_id, attempts - 1)

      [{pid, _}] ->
        assert Process.alive?(pid)
    end
  end

  defp assert_registered(scene_id, 0), do: flunk("scene #{scene_id} was not registered")

  defp small_writer do
    ~S"""
    import math
    import struct
    import sys
    from pathlib import Path

    output = Path(sys.argv[1]) / "contract"
    output.mkdir(parents=True)
    (output / "b04.f32").write_bytes(struct.pack("<ffff", 0.125, math.nan, 0.25, 0.375))
    (output / "b08.f32").write_bytes(struct.pack("<ffff", 0.5, math.nan, 0.75, 0.875))
    """
  end

  defp interrupted_writer do
    ~S"""
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("--safe")
    parser.add_argument("--root")
    args = parser.parse_args()
    scene = Path(args.safe).stem
    partial = Path(args.root) / "fixtures" / "sentinel-2" / "scenes" / scene / "prepared.partial"
    partial.mkdir(parents=True)
    (partial / "orphan.partial").write_bytes(b"partial")
    raise SystemExit(8)
    """
  end

  defp contract_publisher do
    ~S"""
    import argparse
    import hashlib
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("--safe")
    parser.add_argument("--root")
    args = parser.parse_args()
    root = Path(args.root)
    scene = Path(args.safe).stem
    fixture = root / "fixtures" / "sentinel-2"
    manifest_path = fixture / "manifest.json"
    if manifest_path.exists():
        raise SystemExit(0)

    product_id = "S2A_MSIL2A_CONTROLLED"
    source_checksum = "a" * 64
    scene_dir = fixture / "scenes" / scene
    prepared = scene_dir / "prepared"
    crop_paths = []

    for size, size_class in ((1024, "small"), (4096, "medium"), (8192, "large")):
        crop = prepared / f"{size}x{size}"
        crop.mkdir(parents=True, exist_ok=True)
        checksums = {}
        paths = {}
        for band in ("b04", "b08"):
            binary = crop / f"{band}.f32"
            with binary.open("wb") as output:
                output.truncate(size * size * 4)
            digest = hashlib.sha256()
            with binary.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
            checksums[band] = digest.hexdigest()
            paths[band] = binary.relative_to(root).as_posix()

        metadata_path = crop / "metadata.json"
        relative_metadata = metadata_path.relative_to(root).as_posix()
        metadata = {
            "product_id": product_id,
            "tile_id": "T22JCP",
            "sensing_time_utc": "2024-08-30T13:22:41Z",
            "size_class": size_class,
            "source_b04": "fixtures/sentinel-2/source/B04.jp2",
            "source_b08": "fixtures/sentinel-2/source/B08.jp2",
            "width": size,
            "height": size,
            "data_type": "float32",
            "byte_order": "little-endian",
            "memory_order": "row-major",
            "crs": "EPSG:32722",
            "pixel_size": [10.0, -10.0],
            "origin": [500000.0, 7200000.0],
            "row_offset": 0,
            "column_offset": 0,
            "boa_offset_b04": -1000.0,
            "boa_offset_b08": -1000.0,
            "boa_quantification_value": 10000.0,
            "source_nodata_value": 0,
            "source_saturated_value": 65535,
            "checksum_b04_prepared": checksums["b04"],
            "checksum_b08_prepared": checksums["b08"],
            "path_b04": paths["b04"],
            "path_b08": paths["b08"],
            "metadata_path": relative_metadata,
            "preview_path": (crop / "preview.png").relative_to(root).as_posix(),
        }
        metadata_path.write_text(json.dumps(metadata))
        crop_paths.append(relative_metadata)

    scene_dir.mkdir(parents=True, exist_ok=True)
    (scene_dir / "source.json").write_text(json.dumps({
        "product_id": product_id,
        "source_checksum": source_checksum,
    }))
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({
        "schema_version": 1,
        "scenes": {scene: {
            "status": "prepared",
            "product_id": product_id,
            "source_checksum": source_checksum,
            "crops": crop_paths,
        }},
    }))
    """
  end
end
