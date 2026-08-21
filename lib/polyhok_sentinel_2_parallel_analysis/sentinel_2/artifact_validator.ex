defmodule PolyhokSentinel2ParallelAnalysis.Sentinel2.ArtifactValidator do
  @moduledoc "Validates the filesystem contract published by the Python preparer."

  @crop_sizes [1024, 4096, 8192]
  @required_fields ~w(
    product_id tile_id sensing_time_utc size_class source_b04 source_b08
    width height data_type byte_order memory_order crs pixel_size origin
    row_offset column_offset boa_offset_b04 boa_offset_b08
    boa_quantification_value source_nodata_value source_saturated_value
    checksum_b04_prepared checksum_b08_prepared path_b04 path_b08
    metadata_path preview_path
  )

  @spec validate(Path.t(), String.t()) :: {:ok, map()} | {:error, term()}
  def validate(project_root, scene_id) when is_binary(scene_id) do
    root = Path.expand(project_root)
    manifest_path = Path.join(root, "fixtures/sentinel-2/manifest.json")

    with {:ok, manifest} <- read_json(manifest_path),
         :ok <- require_manifest(manifest),
         {:ok, entry} <- prepared_entry(manifest, scene_id),
         :ok <- validate_source(root, scene_id, entry),
         {:ok, crops} <- validate_crops(root, entry) do
      {:ok,
       %{
         scene_id: scene_id,
         product_id: entry["product_id"],
         source_checksum: entry["source_checksum"],
         crops: crops
       }}
    end
  end

  defp read_json(path) do
    with {:ok, body} <- File.read(path),
         {:ok, value} <- Jason.decode(body),
         true <- is_map(value) do
      {:ok, value}
    else
      false -> {:error, {:invalid_json_object, relative_label(path)}}
      {:error, %Jason.DecodeError{}} -> {:error, {:invalid_json, relative_label(path)}}
      {:error, reason} -> {:error, {:unreadable_file, relative_label(path), reason}}
    end
  end

  defp require_manifest(%{"schema_version" => 1, "scenes" => scenes}) when is_map(scenes),
    do: :ok

  defp require_manifest(_), do: {:error, :invalid_manifest}

  defp prepared_entry(manifest, scene_id) do
    case get_in(manifest, ["scenes", scene_id]) do
      %{
        "status" => "prepared",
        "product_id" => product_id,
        "source_checksum" => checksum,
        "crops" => crops
      } = entry
      when is_binary(product_id) and is_binary(checksum) and is_list(crops) ->
        {:ok, entry}

      nil ->
        {:error, :scene_not_prepared}

      _ ->
        {:error, :invalid_scene_entry}
    end
  end

  defp validate_source(root, scene_id, entry) do
    path = Path.join([root, "fixtures", "sentinel-2", "scenes", scene_id, "source.json"])

    with {:ok, source} <- read_json(path),
         true <- source["product_id"] == entry["product_id"],
         true <- source["source_checksum"] == entry["source_checksum"] do
      :ok
    else
      false -> {:error, :stale_source}
      {:error, reason} -> {:error, reason}
    end
  end

  defp validate_crops(root, %{"crops" => paths} = entry) do
    with true <- length(paths) == 3,
         {:ok, crops} <- map_while_ok(paths, &validate_crop(root, &1, entry)),
         true <- Enum.map(crops, & &1["width"]) |> Enum.sort() == @crop_sizes do
      {:ok, Enum.sort_by(crops, & &1["width"])}
    else
      false -> {:error, :invalid_crop_set}
      {:error, reason} -> {:error, reason}
    end
  end

  defp validate_crop(root, relative_metadata, entry) do
    with {:ok, metadata_path} <- resolve_inside(root, relative_metadata),
         {:ok, metadata} <- read_json(metadata_path),
         :ok <- require_fields(metadata),
         :ok <- validate_metadata_contract(metadata, relative_metadata, entry),
         :ok <- validate_metadata_paths(root, metadata),
         :ok <- validate_band(root, metadata, "b04"),
         :ok <- validate_band(root, metadata, "b08") do
      {:ok, metadata}
    end
  end

  defp require_fields(metadata) do
    case Enum.reject(@required_fields, &Map.has_key?(metadata, &1)) do
      [] -> :ok
      missing -> {:error, {:missing_metadata_fields, missing}}
    end
  end

  defp validate_metadata_contract(metadata, relative_metadata, entry) do
    width = metadata["width"]

    valid =
      width in @crop_sizes and metadata["height"] == width and
        metadata["metadata_path"] == relative_metadata and
        metadata["product_id"] == entry["product_id"] and
        metadata["data_type"] == "float32" and
        metadata["byte_order"] == "little-endian" and
        metadata["memory_order"] == "row-major" and
        valid_pair?(metadata["pixel_size"]) and valid_pair?(metadata["origin"])

    if valid, do: :ok, else: {:error, :invalid_crop_metadata}
  end

  defp valid_pair?([left, right]), do: is_number(left) and is_number(right)
  defp valid_pair?(_), do: false

  defp validate_metadata_paths(root, metadata) do
    Enum.reduce_while(~w(source_b04 source_b08 preview_path), :ok, fn field, :ok ->
      case resolve_inside(root, metadata[field]) do
        {:ok, _path} -> {:cont, :ok}
        {:error, reason} -> {:halt, {:error, reason}}
      end
    end)
  end

  defp validate_band(root, metadata, band) do
    path_key = "path_#{band}"
    checksum_key = "checksum_#{band}_prepared"
    expected_bytes = metadata["width"] * metadata["height"] * 4

    with {:ok, path} <- resolve_inside(root, metadata[path_key]),
         {:ok, stat} <- File.stat(path),
         true <- stat.type == :regular and stat.size == expected_bytes,
         {:ok, checksum} <- checksum(path),
         true <- checksum == metadata[checksum_key] do
      :ok
    else
      false -> {:error, {:invalid_artifact, band}}
      {:error, reason} when is_atom(reason) -> {:error, {:unreadable_artifact, band, reason}}
      {:error, reason} -> {:error, reason}
    end
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

  defp checksum(path) do
    case File.open(path, [:read, :binary]) do
      {:ok, device} ->
        digest = checksum_chunks(device, :crypto.hash_init(:sha256))
        File.close(device)
        {:ok, Base.encode16(:crypto.hash_final(digest), case: :lower)}

      {:error, reason} ->
        {:error, reason}
    end
  end

  defp checksum_chunks(device, digest) do
    case IO.binread(device, 1_048_576) do
      :eof -> digest
      {:error, reason} -> throw({:checksum_read_error, reason})
      bytes -> checksum_chunks(device, :crypto.hash_update(digest, bytes))
    end
  end

  defp map_while_ok(values, function) do
    Enum.reduce_while(values, {:ok, []}, fn value, {:ok, acc} ->
      case function.(value) do
        {:ok, item} -> {:cont, {:ok, [item | acc]}}
        {:error, reason} -> {:halt, {:error, reason}}
      end
    end)
    |> case do
      {:ok, items} -> {:ok, Enum.reverse(items)}
      error -> error
    end
  end

  defp relative_label(path), do: Path.basename(path)
end
