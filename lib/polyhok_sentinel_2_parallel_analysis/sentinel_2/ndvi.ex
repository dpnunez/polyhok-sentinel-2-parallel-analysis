defmodule PolyhokSentinel2ParallelAnalysis.Sentinel2.Ndvi do
  @moduledoc "Calculates NDVI on the GPU through PolyHok."

  require PolyHok

  @spec compute(Nx.Tensor.t(), Nx.Tensor.t()) :: Nx.Tensor.t()
  def compute(b04, b08) do
    validate_inputs!(b04, b08)

    {gpu_b04, gpu_b08} = to_device(b04, b08)

    gpu_b04
    |> run_kernel(gpu_b08)
    |> to_host()
  end

  @spec to_device(Nx.Tensor.t(), Nx.Tensor.t()) :: {term(), term()}
  def to_device(b04, b08), do: {PolyHok.new_gnx(b04), PolyHok.new_gnx(b08)}

  @spec run_kernel(term(), term()) :: term()
  def run_kernel(gpu_b04, gpu_b08) do
    register_ske_kernel()

    Ske.map2(
      gpu_b04,
      gpu_b08,
      PolyHok.phok(fn b04, b08 ->
        if b08 + b04 != b08 + b04 || b08 + b04 == 0.0 do
          return((b08 + b04) / (b08 + b04))
        else
          return((b08 - b04) / (b08 + b04))
        end

        return(b04)
      end)
    )
  end

  @spec to_host(term()) :: Nx.Tensor.t()
  def to_host(gpu_ndvi), do: PolyHok.get_gnx(gpu_ndvi)

  # SPEC_DEVIATION: Restore Ske's JIT metadata in a compiled Mix application.
  # Reason: PolyHok keeps the metadata only in a process linked to its compiler.
  defp register_ske_kernel do
    ast =
      quote do
        defk map2_kernel(a1, a2, a3, size, f) do
          id = blockIdx.x * blockDim.x + threadIdx.x

          if id < size do
            a3[id] = f(a1[id], a2[id])
          end
        end
      end

    ast =
      Macro.prewalk(ast, fn
        {name, metadata, context} when is_atom(name) and is_atom(context) ->
          {name, metadata, nil}

        node ->
          node
      end)

    JIT.process_module(Ske, ast)
  end

  defp validate_inputs!(b04, b08) do
    validate_tensor!(b04, "B04")
    validate_tensor!(b08, "B08")

    if Nx.shape(b04) != Nx.shape(b08) do
      raise ArgumentError, "B04 and B08 must have the same shape"
    end
  end

  defp validate_tensor!(%Nx.Tensor{} = tensor, name) do
    if Nx.type(tensor) != {:f, 32} do
      raise ArgumentError, "#{name} must have type {:f, 32}"
    end

    case Nx.shape(tensor) do
      {height, width} when height > 0 and width > 0 -> :ok
      _ -> raise ArgumentError, "#{name} must be a non-empty two-dimensional tensor"
    end
  end

  defp validate_tensor!(_tensor, name) do
    raise ArgumentError, "#{name} must be an Nx tensor"
  end
end
