# Demo transcript

Commands run from `backend/` with Ollama available (`llama3.2` or another
tool-capable model).

## Seed / schema

```bash
python -m scripts.init_db --reset
```

Expected counts: categories 4, products 10, customers 6, orders 10, order_items 19.

## CLI ask

```bash
python -m scripts.ask "Show the top 5 products by sales"
```

Expected shape:

- `Success: True`
- SQL joining `order_items`, `products` (and usually `orders`)
- Top row near `4K Monitor` / `658`

## HTTP query

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/examples
curl -s -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"How many products are in the catalog?\"}"
```

## Evaluation

```bash
python -m scripts.eval_accuracy --gold-only
python -m scripts.eval_accuracy --agent --limit 5
```

`--gold-only` should report accuracy-ready gold SQL for all cases.
`--agent` scores execution accuracy against those gold result sets.
