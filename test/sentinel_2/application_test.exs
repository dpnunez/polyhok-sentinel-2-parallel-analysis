defmodule PolyhokSentinel2ParallelAnalysis.Sentinel2.ApplicationTest do
  use ExUnit.Case, async: true

  alias PolyhokSentinel2ParallelAnalysis.Sentinel2

  test "starts the unique preparation registry" do
    assert Process.alive?(Process.whereis(Sentinel2.PreparationRegistry))
    assert Registry.lookup(Sentinel2.PreparationRegistry, "scene-a") == []
  end

  test "starts the dynamic worker supervisor" do
    supervisor = Process.whereis(Sentinel2.PreparationSupervisor)

    assert Process.alive?(supervisor)
    assert %{active: 0, specs: 0} = DynamicSupervisor.count_children(supervisor)
  end

  test "supervises both preparation services with one-for-one strategy" do
    supervisor = Process.whereis(PolyhokSentinel2ParallelAnalysis.Supervisor)

    assert {:state, _, :one_for_one, _, _, _, _, _, _, _, _, _} = :sys.get_state(supervisor)
    assert 2 = Supervisor.count_children(supervisor).active
  end
end
