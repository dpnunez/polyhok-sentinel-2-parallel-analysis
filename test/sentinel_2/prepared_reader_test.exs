defmodule PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparedReaderTest do
  use ExUnit.Case, async: true

  alias PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparedReader

  test "reads both little-endian row-major bands from the project root" do
    root = fixture_root()
    metadata = write_crop(root, [1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0])

    assert {:ok, %{b04: b04, b08: b08}} = PreparedReader.read_crop(root, metadata)
    assert Nx.type(b04) == {:f, 32}
    assert Nx.type(b08) == {:f, 32}
    assert Nx.shape(b04) == {2, 2}
    assert Nx.shape(b08) == {2, 2}
    assert Nx.to_flat_list(b04) == [1.0, 2.0, 3.0, 4.0]
    assert Nx.to_flat_list(b08) == [5.0, 6.0, 7.0, 8.0]
  end

  test "preserves NaN positions in both tensors" do
    root = fixture_root()
    metadata = write_crop(root, [1.0, :nan, 3.0, 4.0], [5.0, :nan, 7.0, 8.0])

    assert {:ok, %{b04: b04, b08: b08}} = PreparedReader.read_crop(root, metadata)
    assert [1.0, :nan, 3.0, 4.0] = Nx.to_flat_list(b04)
    assert [5.0, :nan, 7.0, 8.0] = Nx.to_flat_list(b08)
  end

  test "returns the exact byte-size error before tensor construction" do
    root = fixture_root()
    metadata = write_crop(root, [1.0], [2.0])

    assert {:error, :invalid_byte_size} = PreparedReader.read_crop(root, metadata)
  end

  test "rejects a relative path that escapes the project root" do
    root = fixture_root()
    metadata = %{"width" => 1, "height" => 1, "path_b04" => "../b04.f32", "path_b08" => "b08.f32"}

    assert {:error, :path_outside_project_root} = PreparedReader.read_crop(root, metadata)
  end

  test "returns a tagged error when a band cannot be read" do
    root = fixture_root()

    metadata = %{
      "width" => 1,
      "height" => 1,
      "path_b04" => "missing.f32",
      "path_b08" => "b08.f32"
    }

    assert {:error, {:unreadable_band, :enoent}} = PreparedReader.read_crop(root, metadata)
  end

  test "swaps every 32-bit word for a big-endian host" do
    little = <<1, 2, 3, 4, 5, 6, 7, 8>>

    assert PreparedReader.normalize_little_endian(little, :big) ==
             <<4, 3, 2, 1, 8, 7, 6, 5>>
  end

  test "does not copy or alter bytes for a little-endian host" do
    little = <<1, 2, 3, 4>>

    assert :erts_debug.same(little, PreparedReader.normalize_little_endian(little, :little))
  end

  defp fixture_root do
    path = Path.join(System.tmp_dir!(), "prepared-reader-#{System.unique_integer([:positive])}")
    on_exit(fn -> File.rm_rf!(path) end)
    File.mkdir_p!(path)
    path
  end

  defp write_crop(root, b04, b08) do
    File.write!(Path.join(root, "b04.f32"), encode(b04))
    File.write!(Path.join(root, "b08.f32"), encode(b08))

    %{
      "width" => 2,
      "height" => 2,
      "path_b04" => "b04.f32",
      "path_b08" => "b08.f32"
    }
  end

  defp encode(values) do
    for value <- values, into: <<>> do
      case value do
        :nan -> <<0x7FC00000::little-unsigned-integer-size(32)>>
        number -> <<number::little-float-size(32)>>
      end
    end
  end
end
