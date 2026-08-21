defmodule PolyhokSentinel2ParallelAnalysis.Sentinel2.ArtifactValidatorTest do
  use ExUnit.Case, async: true

  alias PolyhokSentinel2ParallelAnalysis.Sentinel2.ArtifactValidator

  @scene_id "s2a-t22jcp-20240830t132241"
  @product_id "S2A_MSIL2A_TEST"
  @checksum String.duplicate("a", 64)
  @sizes [1024, 4096, 8192]

  test "accepts one prepared scene with the three complete crops" do
    root = fixture_root()
    write_contract(root, create_binaries: true)

    assert {:ok, prepared} = ArtifactValidator.validate(root, @scene_id)
    assert prepared.scene_id == @scene_id
    assert prepared.product_id == @product_id
    assert prepared.source_checksum == @checksum
    assert Enum.map(prepared.crops, & &1["width"]) == @sizes
    assert Enum.all?(prepared.crops, &is_binary(&1["path_b04"]))
    assert Enum.all?(prepared.crops, &is_binary(&1["path_b08"]))
  end

  test "rejects invalid manifest JSON" do
    root = fixture_root()
    manifest = manifest_path(root)
    File.mkdir_p!(Path.dirname(manifest))
    File.write!(manifest, "{")

    assert {:error, {:invalid_json, "manifest.json"}} =
             ArtifactValidator.validate(root, @scene_id)
  end

  test "rejects a scene without a prepared manifest entry" do
    root = fixture_root()
    write_json(manifest_path(root), %{"schema_version" => 1, "scenes" => %{}})

    assert {:error, :scene_not_prepared} = ArtifactValidator.validate(root, @scene_id)
  end

  test "rejects a crop set other than 1024, 4096 and 8192" do
    root = fixture_root()
    write_contract(root, crops: [crop_path(1024)])

    assert {:error, :invalid_crop_set} = ArtifactValidator.validate(root, @scene_id)
  end

  test "rejects paths that escape the configured project root" do
    root = fixture_root()
    write_contract(root, metadata_overrides: %{"preview_path" => "../preview.png"})

    assert {:error, :path_outside_project_root} =
             ArtifactValidator.validate(root, @scene_id)
  end

  test "rejects metadata with required fields missing" do
    root = fixture_root()
    write_contract(root, drop_field: "crs")

    assert {:error, {:missing_metadata_fields, ["crs"]}} =
             ArtifactValidator.validate(root, @scene_id)
  end

  test "rejects missing prepared binaries" do
    root = fixture_root()
    write_contract(root)

    assert {:error, {:unreadable_artifact, "b04", :enoent}} =
             ArtifactValidator.validate(root, @scene_id)
  end

  test "rejects a binary whose byte size does not match metadata" do
    root = fixture_root()
    write_contract(root)
    File.write!(Path.join(root, band_path(1024, "b04")), <<0>>)

    assert {:error, {:invalid_artifact, "b04"}} =
             ArtifactValidator.validate(root, @scene_id)
  end

  test "rejects a checksum mismatch" do
    root = fixture_root()
    write_contract(root)
    binary = Path.join(root, band_path(1024, "b04"))
    write_sparse(binary, 1024 * 1024 * 4)

    assert {:error, {:invalid_artifact, "b04"}} =
             ArtifactValidator.validate(root, @scene_id)
  end

  test "rejects a source identity that differs from the manifest" do
    root = fixture_root()
    write_contract(root, source_checksum: String.duplicate("b", 64))

    assert {:error, :stale_source} = ArtifactValidator.validate(root, @scene_id)
  end

  defp fixture_root do
    path =
      Path.join(System.tmp_dir!(), "artifact-validator-#{System.unique_integer([:positive])}")

    on_exit(fn -> File.rm_rf!(path) end)
    path
  end

  defp write_contract(root, options \\ []) do
    crops = Keyword.get(options, :crops, Enum.map(@sizes, &crop_path/1))

    entry = %{
      "status" => "prepared",
      "product_id" => @product_id,
      "source_checksum" => @checksum,
      "crops" => crops
    }

    write_json(manifest_path(root), %{
      "schema_version" => 1,
      "scenes" => %{@scene_id => entry}
    })

    write_json(source_path(root), %{
      "product_id" => @product_id,
      "source_checksum" => Keyword.get(options, :source_checksum, @checksum)
    })

    Enum.each(@sizes, fn size ->
      metadata =
        crop_metadata(size)
        |> Map.merge(Keyword.get(options, :metadata_overrides, %{}))
        |> Map.delete(Keyword.get(options, :drop_field, ""))

      if Keyword.get(options, :create_binaries, false) do
        metadata =
          Enum.reduce(~w(b04 b08), metadata, fn band, acc ->
            path = Path.join(root, band_path(size, band))
            write_sparse(path, size * size * 4)
            Map.put(acc, "checksum_#{band}_prepared", sha256(path))
          end)

        write_json(Path.join(root, crop_path(size)), metadata)
      else
        write_json(Path.join(root, crop_path(size)), metadata)
      end
    end)
  end

  defp crop_metadata(size) do
    base = "fixtures/sentinel-2/scenes/#{@scene_id}/prepared/#{size}x#{size}"

    %{
      "product_id" => @product_id,
      "tile_id" => "T22JCP",
      "sensing_time_utc" => "2024-08-30T13:22:41Z",
      "size_class" => size_class(size),
      "source_b04" => "fixtures/sentinel-2/source/B04.jp2",
      "source_b08" => "fixtures/sentinel-2/source/B08.jp2",
      "width" => size,
      "height" => size,
      "data_type" => "float32",
      "byte_order" => "little-endian",
      "memory_order" => "row-major",
      "crs" => "EPSG:32722",
      "pixel_size" => [10.0, -10.0],
      "origin" => [500_000.0, 7_200_000.0],
      "row_offset" => 0,
      "column_offset" => 0,
      "boa_offset_b04" => -1000.0,
      "boa_offset_b08" => -1000.0,
      "boa_quantification_value" => 10_000.0,
      "source_nodata_value" => 0,
      "source_saturated_value" => 65_535,
      "checksum_b04_prepared" => String.duplicate("0", 64),
      "checksum_b08_prepared" => String.duplicate("0", 64),
      "path_b04" => "#{base}/b04.f32",
      "path_b08" => "#{base}/b08.f32",
      "metadata_path" => "#{base}/metadata.json",
      "preview_path" => "#{base}/preview.png"
    }
  end

  defp write_sparse(path, size) do
    File.mkdir_p!(Path.dirname(path))
    {:ok, device} = File.open(path, [:write, :binary])
    {:ok, _} = :file.position(device, size - 1)
    :ok = IO.binwrite(device, <<0>>)
    File.close(device)
  end

  defp sha256(path) do
    digest =
      path
      |> File.stream!([], 1_048_576)
      |> Enum.reduce(:crypto.hash_init(:sha256), &:crypto.hash_update(&2, &1))

    :crypto.hash_final(digest) |> Base.encode16(case: :lower)
  end

  defp write_json(path, value) do
    File.mkdir_p!(Path.dirname(path))
    File.write!(path, Jason.encode!(value))
  end

  defp manifest_path(root), do: Path.join(root, "fixtures/sentinel-2/manifest.json")

  defp source_path(root),
    do: Path.join(root, "fixtures/sentinel-2/scenes/#{@scene_id}/source.json")

  defp crop_path(size),
    do: "fixtures/sentinel-2/scenes/#{@scene_id}/prepared/#{size}x#{size}/metadata.json"

  defp band_path(size, band),
    do: "fixtures/sentinel-2/scenes/#{@scene_id}/prepared/#{size}x#{size}/#{band}.f32"

  defp size_class(1024), do: "small"
  defp size_class(4096), do: "medium"
  defp size_class(8192), do: "large"
end
