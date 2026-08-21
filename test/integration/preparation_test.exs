defmodule PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparationTest do
  use ExUnit.Case, async: false

  alias PolyhokSentinel2ParallelAnalysis.Sentinel2.Preparation
  alias PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparationRegistry

  test "returns only the prepared tagged tuple on success" do
    root = fixture_root()
    scene = scene("success")
    validator = fn _, scene_id -> {:ok, %{scene_id: scene_id, crops: []}} end

    assert {:ok, %{scene_id: "success", crops: []}} =
             Preparation.prepare(
               scene,
               worker_options(root, "exit 0", validator: validator)
             )

    assert_registry_released("success")
  end

  test "returns only an error tagged tuple on process failure" do
    root = fixture_root()

    assert {:error, {:process_failed, 4, "failed"}} =
             Preparation.prepare(scene("failure"), worker_options(root, "printf failed; exit 4"))

    assert_registry_released("failure")
  end

  test "keeps unrelated BEAM processes running while the caller waits" do
    root = fixture_root()
    parent = self()

    ticker =
      spawn(fn ->
        Process.sleep(20)
        send(parent, :unrelated_process_ran)
      end)

    assert {:error, {:process_failed, 1, ""}} =
             Preparation.prepare(scene("wait"), worker_options(root, "sleep 0.08; exit 1"))

    assert_received :unrelated_process_ran
    refute Process.alive?(ticker)
  end

  test "rejects a second active request for the same scene" do
    root = fixture_root()
    scene = scene("duplicate")
    options = worker_options(root, "sleep 0.15; exit 1")
    first = Task.async(fn -> Preparation.prepare(scene, options) end)
    assert_registered("duplicate")

    assert {:error, :already_running} = Preparation.prepare(scene, options)
    assert {:error, {:process_failed, 1, ""}} = Task.await(first, 1_000)
    assert_registry_released("duplicate")
  end

  test "releases the unique name after timeout so the scene can run again" do
    root = fixture_root()
    scene = scene("timeout")

    assert {:error, :timeout} =
             Preparation.prepare(scene, worker_options(root, "sleep 2", timeout: 20))

    assert_registry_released("timeout")

    assert {:error, {:process_failed, 2, ""}} =
             Preparation.prepare(scene, worker_options(root, "exit 2"))

    assert_registry_released("timeout")
  end

  test "returns a tagged input error without starting a worker" do
    assert {:error, :invalid_scene} = Preparation.prepare(%{scene_id: "missing-safe"})
    assert Registry.lookup(PreparationRegistry, "missing-safe") == []
  end

  defp worker_options(root, body, extra \\ []) do
    [
      project_root: root,
      executable: "/bin/sh",
      entrypoint: script(root, body),
      timeout: 1_000
    ]
    |> Keyword.merge(extra)
  end

  defp scene(id), do: %{scene_id: id, safe_path: "/tmp/#{id}.SAFE"}

  defp fixture_root do
    path = Path.join(System.tmp_dir!(), "preparation-api-#{System.unique_integer([:positive])}")
    File.mkdir_p!(path)
    on_exit(fn -> File.rm_rf!(path) end)
    path
  end

  defp script(root, body) do
    path = Path.join(root, "api-script-#{System.unique_integer([:positive])}.sh")
    File.write!(path, "#!/bin/sh\n#{body}\n")
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

  defp assert_registry_released(scene_id, attempts \\ 50)

  defp assert_registry_released(scene_id, attempts) when attempts > 0 do
    case Registry.lookup(PreparationRegistry, scene_id) do
      [] ->
        :ok

      _ ->
        Process.sleep(5)
        assert_registry_released(scene_id, attempts - 1)
    end
  end

  defp assert_registry_released(scene_id, 0), do: flunk("scene #{scene_id} remains registered")
end
