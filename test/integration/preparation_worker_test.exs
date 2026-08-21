defmodule PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparationWorkerTest do
  use ExUnit.Case, async: true

  import ExUnit.CaptureLog

  alias PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparationWorker

  @scene_id "scene-worker-test"

  test "returns executable_not_found when the interpreter is absent" do
    root = fixture_root()

    assert {:error, :executable_not_found} =
             run_worker(root, executable: Path.join(root, "missing-python"))
  end

  test "returns executable_not_found when the entrypoint is absent" do
    root = fixture_root()

    assert {:error, :executable_not_found} =
             run_worker(root, entrypoint: Path.join(root, "missing.py"))
  end

  test "returns process_failed only after a nonzero exit status" do
    root = fixture_root()
    script = script(root, "printf partial; sleep 0.05; printf done; exit 7")

    assert {:error, {:process_failed, 7, "partialdone"}} = run_worker(root, entrypoint: script)
  end

  test "passes entrypoint and CLI values as separate arguments" do
    root = Path.join(fixture_root(), "root with spaces")
    File.mkdir_p!(root)
    script = script(root, ~S(printf '%s|%s|%s|%s' "$1" "$2" "$3" "$4"; exit 9))

    assert {:error, {:process_failed, 9, diagnostic}} =
             run_worker(root, entrypoint: script, safe_path: Path.join(root, "input scene.SAFE"))

    assert diagnostic == "--safe|#{Path.join(root, "input scene.SAFE")}|--root|#{root}"
  end

  test "validates artifacts only after status zero and returns prepared scene" do
    root = fixture_root()
    script = script(root, "printf ok; exit 0")
    parent = self()

    validator = fn received_root, received_scene ->
      send(parent, {:validated, received_root, received_scene})
      {:ok, %{scene_id: received_scene}}
    end

    assert {:ok, %{scene_id: @scene_id}} =
             run_worker(root, entrypoint: script, validator: validator)

    assert_received {:validated, ^root, @scene_id}
  end

  test "does not validate artifacts after a nonzero status" do
    root = fixture_root()
    script = script(root, "exit 2")
    validator = fn _, _ -> flunk("validator must not run") end

    assert {:error, {:process_failed, 2, ""}} =
             run_worker(root, entrypoint: script, validator: validator)
  end

  test "propagates validation failure after status zero" do
    root = fixture_root()
    script = script(root, "exit 0")
    validator = fn _, _ -> {:error, :invalid_manifest} end

    assert {:error, :invalid_manifest} =
             run_worker(root, entrypoint: script, validator: validator)
  end

  test "closes the port and returns timeout" do
    root = fixture_root()
    script = script(root, "sleep 2; printf late; exit 0")

    assert {:error, :timeout} = run_worker(root, entrypoint: script, timeout: 20)
  end

  test "terminates after timeout and cannot change the reported result with late output" do
    root = fixture_root()
    script = script(root, "sleep 2; printf late; exit 0")
    {pid, reference} = start_worker(root, entrypoint: script, timeout: 20)
    _monitor = Process.monitor(pid)

    assert_receive {^reference, {:error, :timeout}}, 500
    assert_receive {:DOWN, _, :process, ^pid, :normal}, 500
    refute_receive {^reference, _}, 100
  end

  test "emits one bounded terminal log without unbounded diagnostic bytes" do
    root = fixture_root()
    script = script(root, "head -c 5000 /dev/zero | tr '\\0' x; exit 3")

    log =
      capture_log(fn ->
        assert {:error, {:process_failed, 3, diagnostic}} = run_worker(root, entrypoint: script)
        assert byte_size(diagnostic) == 4096
      end)

    assert log =~ "scene_id=#{@scene_id}"
    assert log =~ "duration_ms="
    assert log =~ "result=error"
    assert byte_size(log) < 4500
  end

  defp run_worker(root, options) do
    {_pid, reference} = start_worker(root, options)
    assert_receive {^reference, result}, 2_500
    result
  end

  defp start_worker(root, options) do
    reference = make_ref()

    defaults = [
      scene_id: @scene_id,
      safe_path: Path.join(root, "input.SAFE"),
      project_root: root,
      executable: "/bin/sh",
      entrypoint: script(root, "exit 0"),
      timeout: 1_000,
      reply_to: self(),
      reply_ref: reference
    ]

    {:ok, pid} = PreparationWorker.start_link(Keyword.merge(defaults, options))
    {pid, reference}
  end

  defp fixture_root do
    path =
      Path.join(System.tmp_dir!(), "preparation-worker-#{System.unique_integer([:positive])}")

    File.mkdir_p!(path)
    on_exit(fn -> File.rm_rf!(path) end)
    path
  end

  defp script(root, body) do
    path = Path.join(root, "script-#{System.unique_integer([:positive])}.sh")
    File.mkdir_p!(Path.dirname(path))
    File.write!(path, "#!/bin/sh\n#{body}\n")
    path
  end
end
