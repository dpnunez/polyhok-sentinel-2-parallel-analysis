defmodule PolyhokSentinel2ParallelAnalysis.Application do
  @moduledoc false

  use Application

  @impl true
  def start(_type, _args) do
    children = [
      {Registry,
       keys: :unique, name: PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparationRegistry},
      {DynamicSupervisor,
       strategy: :one_for_one,
       name: PolyhokSentinel2ParallelAnalysis.Sentinel2.PreparationSupervisor}
    ]

    Supervisor.start_link(children,
      strategy: :one_for_one,
      name: PolyhokSentinel2ParallelAnalysis.Supervisor
    )
  end
end
