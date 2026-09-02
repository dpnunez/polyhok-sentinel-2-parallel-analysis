defmodule PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparedReader do
  @moduledoc "Reads validated Sentinel-2 crop binaries into Nx tensors."

  @spec read_crop(Path.t(), map()) ::
          {:ok, %{b04: Nx.Tensor.t(), b08: Nx.Tensor.t()}} | {:error, term()}
  def read_crop(project_root, crop_metadata) when is_map(crop_metadata) do
    root = Path.expand(project_root)

    with {:ok, width, height} <- dimensions(crop_metadata),
         {:ok, b04} <- read_band(root, crop_metadata["path_b04"], width, height),
         {:ok, b08} <- read_band(root, crop_metadata["path_b08"], width, height) do
      {:ok, %{b04: b04, b08: b08}}
    end
  end

  defp dimensions(%{"width" => width, "height" => height})
       when is_integer(width) and width > 0 and is_integer(height) and height > 0,
       do: {:ok, width, height}

  defp dimensions(_), do: {:error, :invalid_metadata}

  defp read_band(root, relative, width, height) do
    with {:ok, path} <- resolve_inside(root, relative),
         {:ok, binary} <- File.read(path),
         true <- byte_size(binary) == width * height * 4 do
      tensor =
        binary
        |> normalize_little_endian(:erlang.system_info(:endian))
        |> Nx.from_binary({:f, 32})
        |> Nx.reshape({height, width})

      {:ok, tensor}
    else
      false -> {:error, :invalid_byte_size}
      {:error, :path_outside_project_root} -> {:error, :path_outside_project_root}
      {:error, reason} when is_atom(reason) -> {:error, {:unreadable_band, reason}}
      {:error, reason} -> {:error, reason}
    end
  end

  @doc false
  def normalize_little_endian(binary, :little), do: binary

  def normalize_little_endian(binary, :big) do
    for <<a, b, c, d <- binary>>, into: <<>>, do: <<d, c, b, a>>
  end

  defp resolve_inside(root, relative) when is_binary(relative) do
    if Path.type(relative) == :relative do
      path = Path.expand(relative, root)
      relative_to_root = Path.relative_to(path, root)

      if Path.type(relative_to_root) == :relative and relative_to_root != ".." and
           not String.starts_with?(relative_to_root, "../") do
        {:ok, path}
      else
        {:error, :path_outside_project_root}
      end
    else
      {:error, :path_outside_project_root}
    end
  end

  defp resolve_inside(_root, _relative), do: {:error, :path_outside_project_root}
end
