defmodule PolyHokTest do
  use ExUnit.Case, async: false

  test "moves an Nx tensor to the GPU and back" do
    tensor = Nx.tensor([[1, 2, 3, 4]], type: {:s, 32})

    result =
      tensor
      |> PolyHok.new_gnx()
      |> PolyHok.get_gnx()

    assert Nx.to_flat_list(result) == [1, 2, 3, 4]
    assert Nx.type(result) == {:s, 32}
    assert Nx.shape(result) == {1, 4}
  end
end
