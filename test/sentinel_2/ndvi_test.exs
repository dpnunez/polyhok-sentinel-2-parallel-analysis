defmodule PolyhokSentinel2ParallelAnalysis.Sentinel2.NdviTest do
  use ExUnit.Case, async: false

  alias PolyhokSentinel2ParallelAnalysis.Sentinel2.Ndvi

  describe "compute/2 validation" do
    test "rejects either input when it is not an Nx tensor" do
      tensor = Nx.tensor([[1.0]], type: {:f, 32})

      assert_raise ArgumentError, ~r/B04 must be an Nx tensor/, fn ->
        Ndvi.compute(:not_a_tensor, tensor)
      end

      assert_raise ArgumentError, ~r/B08 must be an Nx tensor/, fn ->
        Ndvi.compute(tensor, :not_a_tensor)
      end
    end

    test "rejects either input when it is not float32" do
      float32 = Nx.tensor([[1.0]], type: {:f, 32})
      float64 = Nx.tensor([[1.0]], type: {:f, 64})

      assert_raise ArgumentError, ~r/B04 must have type \{:f, 32\}/, fn ->
        Ndvi.compute(float64, float32)
      end

      assert_raise ArgumentError, ~r/B08 must have type \{:f, 32\}/, fn ->
        Ndvi.compute(float32, float64)
      end
    end

    test "rejects rank other than two" do
      matrix = Nx.tensor([[1.0]], type: {:f, 32})
      vector = Nx.tensor([1.0], type: {:f, 32})

      assert_raise ArgumentError, ~r/B04 must be a non-empty two-dimensional tensor/, fn ->
        Ndvi.compute(vector, matrix)
      end

      assert_raise ArgumentError, ~r/B08 must be a non-empty two-dimensional tensor/, fn ->
        Ndvi.compute(matrix, vector)
      end
    end

    test "rejects a zero-sized dimension" do
      matrix = Nx.tensor([[1.0]], type: {:f, 32})
      empty = %{matrix | shape: {0, 1}, data: %Nx.BinaryBackend{state: <<>>}}

      assert_raise ArgumentError, ~r/B04 must be a non-empty two-dimensional tensor/, fn ->
        Ndvi.compute(empty, matrix)
      end

      assert_raise ArgumentError, ~r/B08 must be a non-empty two-dimensional tensor/, fn ->
        Ndvi.compute(matrix, empty)
      end
    end

    test "rejects different shapes" do
      b04 = Nx.tensor([[1.0, 2.0]], type: {:f, 32})
      b08 = Nx.tensor([[1.0], [2.0]], type: {:f, 32})

      assert_raise ArgumentError, ~r/B04 and B08 must have the same shape/, fn ->
        Ndvi.compute(b04, b08)
      end
    end
  end

  test "propagates the original PolyHok failure at a public GPU boundary" do
    assert_raise FunctionClauseError, fn -> Ndvi.to_host(:invalid_gpu_reference) end
  end

  @tag :gpu
  test "computes the six approved NDVI pixels in one GPU operation" do
    b04 = Nx.tensor([[0.2, 0.4, 0.6], [-0.5, :nan, 0.5]], type: {:f, 32})
    b08 = Nx.tensor([[0.6, 0.4, 0.2], [0.5, 0.5, :nan]], type: {:f, 32})

    result = Ndvi.compute(b04, b08)
    [positive, zero, negative, zero_denominator, nan_b04, nan_b08] = Nx.to_flat_list(result)

    assert Nx.type(result) == {:f, 32}
    assert Nx.shape(result) == {2, 3}
    assert_in_delta positive, 0.5, 1.0e-6
    assert_in_delta zero, 0.0, 1.0e-6
    assert_in_delta negative, -0.5, 1.0e-6
    assert zero_denominator == :nan
    assert nan_b04 == :nan
    assert nan_b08 == :nan
  end

  @tag :gpu
  test "divides by the smallest positive float32 without an epsilon threshold" do
    minimum_subnormal = Nx.from_binary(<<1::native-unsigned-integer-size(32)>>, {:f, 32})
    b04 = Nx.reshape(Nx.tensor([0.0], type: {:f, 32}), {1, 1})
    b08 = Nx.reshape(minimum_subnormal, {1, 1})

    result = Ndvi.compute(b04, b08)

    assert Nx.to_flat_list(result) == [1.0]
  end
end
