defmodule PolyhokSentinel2ParallelAnalysis.Sentinel2.Ndvi.ResultWriterTest do
  use ExUnit.Case, async: true

  alias PolyhokSentinel2ParallelAnalysis.Sentinel2.Ndvi.ResultWriter
  alias PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparedReader

  test "writes reproducible little-endian row-major data and complete metadata" do
    destination = temporary_directory()
    tensor = Nx.tensor([[0.5, 0.0, -0.5], [:nan, 1.0, -1.0]], type: {:f, 32})

    assert {:ok, metadata} = ResultWriter.write(tensor, destination)

    binary_path = Path.join(destination, "ndvi.polyhok.f32")
    metadata_path = Path.join(destination, "metadata.json")
    binary = File.read!(binary_path)

    assert byte_size(binary) == 2 * 3 * 4

    assert binary ==
             <<0.5::little-float-size(32), 0.0::little-float-size(32),
               -0.5::little-float-size(32), 0x7FC00000::little-unsigned-integer-size(32),
               1.0::little-float-size(32), -1.0::little-float-size(32)>>

    assert metadata == %{
             "width" => 3,
             "height" => 2,
             "dtype" => "float32",
             "byte_order" => "little-endian",
             "order" => "row-major",
             "path" => "ndvi.polyhok.f32",
             "sha256" => Base.encode16(:crypto.hash(:sha256, binary), case: :lower)
           }

    assert Jason.decode!(File.read!(metadata_path)) == metadata

    restored =
      binary
      |> PreparedReader.normalize_little_endian(:erlang.system_info(:endian))
      |> Nx.from_binary({:f, 32})
      |> Nx.reshape({metadata["height"], metadata["width"]})

    assert Nx.type(restored) == {:f, 32}
    assert Nx.shape(restored) == {2, 3}
    assert Nx.to_flat_list(restored) == [0.5, 0.0, -0.5, :nan, 1.0, -1.0]
  end

  test "rejects tensors outside the persistence contract without publishing metadata" do
    destination = temporary_directory()

    assert {:error, :invalid_tensor} =
             ResultWriter.write(Nx.tensor([[1.0]], type: {:f, 64}), destination)

    assert {:error, :invalid_tensor} =
             ResultWriter.write(Nx.tensor([1.0], type: {:f, 32}), destination)

    refute File.exists?(Path.join(destination, "metadata.json"))
  end

  test "returns a write error without publishing metadata" do
    destination = temporary_directory()
    partial_binary = Path.join(destination, "ndvi.polyhok.f32.partial")
    File.mkdir_p!(partial_binary)

    assert {:error, :eisdir} =
             ResultWriter.write(Nx.tensor([[1.0]], type: {:f, 32}), destination)

    refute File.exists?(Path.join(destination, "metadata.json"))
  end

  defp temporary_directory do
    path = Path.join(System.tmp_dir!(), "ndvi-result-#{System.unique_integer([:positive])}")
    on_exit(fn -> File.rm_rf!(path) end)
    File.mkdir_p!(path)
    path
  end
end
