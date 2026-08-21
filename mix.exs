defmodule PolyhokSentinel2ParallelAnalysis.MixProject do
  use Mix.Project

  def project do
    [
      app: :polyhok_sentinel_2_parallel_analysis,
      version: "0.1.0",
      elixir: "~> 1.15",
      start_permanent: Mix.env() == :prod,
      deps: deps()
    ]
  end

  def application do
    [
      extra_applications: [:logger],
      mod: {PolyhokSentinel2ParallelAnalysis.Application, []}
    ]
  end

  defp deps do
    [
      {:jason, "~> 1.4"},
      {:poly_hok, path: "/home/daniel/poly_hok"}
    ]
  end
end
