### Environment Setup

This project uses [`uv`](https://github.com/astral-sh/uv) as the Python package manager. Please install `uv` first:

```bash
pip install uv
```

This project also uses [`pnpm`](https://github.com/pnpm/pnpm) as the Node.js package manager. Please install `pnpm` globally:

```bash
npm install -g pnpm
```

Once installed, you can install dependencies by running:

```bash
pnpm install
```
### How to RUN?

You can run the front end and back end separately:

```bash
pnpm dev:next     # Run the frontend (Next.js)
pnpm dev:api      # Run the backend (API server)
```

Or run both together:

```bash
pnpm dev
```

Alternatively, you can run the backend directly using Python and see the output in the terminal:

```bash
uv run python ./src/main.py
```