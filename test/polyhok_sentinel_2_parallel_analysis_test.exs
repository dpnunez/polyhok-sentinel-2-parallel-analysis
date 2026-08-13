defmodule PolyhokSentinel2ParallelAnalysisTest do
  use ExUnit.Case, async: true

  doctest PolyhokSentinel2ParallelAnalysis

  test "greets the world" do
    assert PolyhokSentinel2ParallelAnalysis.hello() == :world
  end
end
