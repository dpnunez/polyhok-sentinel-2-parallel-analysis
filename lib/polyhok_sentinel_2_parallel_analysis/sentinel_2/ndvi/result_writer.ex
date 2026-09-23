defmodule PolyhokSentinel2ParallelAnalysis.Sentinel2.Ndvi.ResultWriter do
  @moduledoc "Writes an NDVI host tensor and its verification metadata."

  alias PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparedReader

  @binary_name "ndvi.polyhok.f32"
  @metadata_name "metadata.json"

  @spec write(Nx.Tensor.t(), Path.t()) :: {:ok, map()} | {:error, term()}
  def write(ndvi, destination) do
    with :ok <- validate_tensor(ndvi),
         :ok <- File.mkdir_p(destination) do
      publish(ndvi, destination)
    end
  end

  defp publish(ndvi, destination) do
    binary_path = Path.join(destination, @binary_name)
    metadata_path = Path.join(destination, @metadata_name)
    partial_binary_path = binary_path <> ".partial"
    partial_metadata_path = metadata_path <> ".partial"

    binary =
      ndvi
      |> Nx.to_binary()
      |> PreparedReader.normalize_little_endian(:erlang.system_info(:endian))

    metadata = metadata(ndvi, binary)

    result =
      with :ok <- File.write(partial_binary_path, binary),
           :ok <- validate_binary(binary, ndvi),
           :ok <- remove_published_metadata(metadata_path),
           :ok <- File.rename(partial_binary_path, binary_path),
           :ok <- File.write(partial_metadata_path, Jason.encode!(metadata)),
           :ok <- File.rename(partial_metadata_path, metadata_path) do
        {:ok, metadata}
      end

    unless match?({:ok, _metadata}, result) do
      File.rm(partial_binary_path)
      File.rm(partial_metadata_path)
    end

    result
  end

  defp validate_tensor(%Nx.Tensor{type: {:f, 32}, shape: {height, width}})
       when height > 0 and width > 0,
       do: :ok

  defp validate_tensor(_ndvi), do: {:error, :invalid_tensor}

  defp validate_binary(binary, %Nx.Tensor{shape: {height, width}}) do
    if byte_size(binary) == height * width * 4, do: :ok, else: {:error, :invalid_byte_size}
  end

  defp remove_published_metadata(path) do
    case File.rm(path) do
      :ok -> :ok
      {:error, :enoent} -> :ok
      {:error, reason} -> {:error, reason}
    end
  end

  defp metadata(%Nx.Tensor{shape: {height, width}}, binary) do
    %{
      "width" => width,
      "height" => height,
      "dtype" => "float32",
      "byte_order" => "little-endian",
      "order" => "row-major",
      "path" => @binary_name,
      "sha256" => Base.encode16(:crypto.hash(:sha256, binary), case: :lower)
    }
  end
end
