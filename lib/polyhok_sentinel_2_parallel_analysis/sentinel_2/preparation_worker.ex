defmodule PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparationWorker do
  @moduledoc false

  use GenServer, restart: :temporary

  require Logger

  alias PolyhokSentinel2ParallelAnalysis.Sentinel2.ArtifactValidator

  @diagnostic_limit 4096

  def start_link(options) do
    GenServer.start_link(__MODULE__, options, Keyword.take(options, [:name]))
  end

  @impl true
  def init(options) do
    state = %{
      scene_id: Keyword.fetch!(options, :scene_id),
      safe_path: Keyword.fetch!(options, :safe_path),
      project_root: Keyword.fetch!(options, :project_root),
      source_uri: Keyword.get(options, :source_uri),
      executable: Keyword.fetch!(options, :executable),
      entrypoint: Keyword.fetch!(options, :entrypoint),
      timeout: Keyword.get(options, :timeout, :timer.hours(1)),
      reply_to: Keyword.fetch!(options, :reply_to),
      reply_ref: Keyword.fetch!(options, :reply_ref),
      validator: Keyword.get(options, :validator, &ArtifactValidator.validate/2),
      started_at: System.monotonic_time(:millisecond),
      port: nil,
      timer: nil,
      diagnostic: <<>>
    }

    {:ok, state, {:continue, :open_port}}
  end

  @impl true
  def handle_continue(:open_port, state) do
    if executable?(state.executable) and File.regular?(state.entrypoint) do
      args =
        [state.entrypoint, "--safe", state.safe_path, "--root", state.project_root] ++
          source_uri_args(state.source_uri)

      port =
        Port.open({:spawn_executable, String.to_charlist(state.executable)}, [
          :binary,
          :exit_status,
          :use_stdio,
          :stderr_to_stdout,
          args: Enum.map(args, &String.to_charlist/1)
        ])

      timer = Process.send_after(self(), :preparation_timeout, state.timeout)
      {:noreply, %{state | port: port, timer: timer}}
    else
      finish({:error, :executable_not_found}, state)
    end
  end

  @impl true
  def handle_info({port, {:data, data}}, %{port: port} = state) do
    diagnostic = bounded_append(state.diagnostic, data)
    {:noreply, %{state | diagnostic: diagnostic}}
  end

  def handle_info({port, {:exit_status, status}}, %{port: port} = state) do
    cancel_timer(state.timer)

    result =
      if status == 0 do
        state.validator.(state.project_root, state.scene_id)
      else
        {:error, {:process_failed, status, state.diagnostic}}
      end

    finish(result, state)
  end

  def handle_info(:preparation_timeout, %{port: port} = state) when is_port(port) do
    Port.close(port)
    finish({:error, :timeout}, %{state | port: nil, timer: nil})
  end

  def handle_info(_late_message, state), do: {:noreply, state}

  defp finish(result, state) do
    duration = System.monotonic_time(:millisecond) - state.started_at
    diagnostic = sanitize_diagnostic(state.diagnostic)

    Logger.info(
      "sentinel2 preparation scene_id=#{state.scene_id} duration_ms=#{duration} " <>
        "result=#{result_label(result)} diagnostic=#{inspect(diagnostic)}"
    )

    send(state.reply_to, {state.reply_ref, result})
    {:stop, :normal, state}
  end

  defp executable?(path), do: File.regular?(path) and not is_nil(System.find_executable(path))

  defp source_uri_args(nil), do: []
  defp source_uri_args(uri), do: ["--source-uri", uri]

  defp bounded_append(existing, data) do
    remaining = max(@diagnostic_limit - byte_size(existing), 0)
    existing <> binary_part(data, 0, min(byte_size(data), remaining))
  end

  defp sanitize_diagnostic(diagnostic) do
    diagnostic
    |> String.replace(~r/[[:cntrl:]&&[^\n\t]]/u, "")
    |> String.trim()
  end

  defp result_label({:ok, _}), do: "ok"

  defp result_label({:error, {:process_failed, status, _diagnostic}}),
    do: "error:process_failed(#{status})"

  defp result_label({:error, reason}), do: "error:#{inspect(reason)}"

  defp cancel_timer(nil), do: :ok
  defp cancel_timer(timer), do: Process.cancel_timer(timer, async: false, info: false)
end
