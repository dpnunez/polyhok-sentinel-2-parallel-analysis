defmodule PolyhokSentinel2ParallelAnalysis.Sentinel2.Preparation do
  @moduledoc "Composable API for supervised Sentinel-2 data preparation."

  alias PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparationWorker

  @registry PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparationRegistry
  @supervisor PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparationSupervisor

  @spec prepare(map(), keyword()) :: {:ok, map()} | {:error, term()}
  def prepare(scene, options \\ [])

  def prepare(%{scene_id: scene_id, safe_path: safe_path}, options)
      when is_binary(scene_id) and is_binary(safe_path) do
    project_root = Keyword.get(options, :project_root, File.cwd!()) |> Path.expand()
    reference = make_ref()
    timeout = Keyword.get(options, :timeout, :timer.hours(1))

    worker_options =
      [
        scene_id: scene_id,
        safe_path: safe_path,
        project_root: project_root,
        source_uri: Keyword.get(options, :source_uri),
        executable: Keyword.get(options, :executable, default_executable(project_root)),
        entrypoint: Keyword.get(options, :entrypoint, default_entrypoint(project_root)),
        timeout: timeout,
        validator: Keyword.get(options, :validator),
        reply_to: self(),
        reply_ref: reference,
        name: {:via, Registry, {@registry, scene_id}}
      ]
      |> Enum.reject(fn {_key, value} -> is_nil(value) end)

    case DynamicSupervisor.start_child(@supervisor, {PreparationWorker, worker_options}) do
      {:ok, _pid} ->
        await_result(reference, timeout)

      {:error, {:already_started, _pid}} ->
        {:error, :already_running}

      {:error, {:shutdown, {:failed_to_start_child, _, {:already_started, _pid}}}} ->
        {:error, :already_running}

      {:error, reason} ->
        {:error, {:worker_start_failed, reason}}
    end
  end

  def prepare(_scene, _options), do: {:error, :invalid_scene}

  defp await_result(reference, timeout) do
    receive do
      {^reference, {:ok, prepared_scene}} -> {:ok, prepared_scene}
      {^reference, {:error, reason}} -> {:error, reason}
    after
      timeout + 5_000 -> {:error, :timeout}
    end
  end

  defp default_executable(root), do: Path.join(root, "python/.venv/bin/python")

  defp default_entrypoint(root),
    do: Path.join(root, "python/src/sentinel2_prepare/cli.py")
end
