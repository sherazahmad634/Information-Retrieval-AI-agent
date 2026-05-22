# Screenshots

Add the following PNGs to this directory once the application is running.
Each placeholder is referenced from the project root `README.md`.

| File                         | Captures                                            |
|------------------------------|-----------------------------------------------------|
| `01-chat.png`                | Chat answering a corpus question, citations expanded |
| `02-tools.png`               | Tool badges (document_search, calculator, remember) |
| `03-upload.png`              | Drag-and-drop document upload + corpus list         |
| `04-search.png`              | Direct `/search` endpoint via Swagger UI            |
| `05-api-docs.png`            | Swagger UI showing the full API surface             |

Suggested capture flow:

1. Start the stack with `docker compose up --build`.
2. Open <http://localhost:3000> and seed the corpus from the sidebar.
3. Ask:
   - "What is reciprocal rank fusion?" → screenshot **01** and **02**.
   - Upload a PDF → screenshot **03**.
4. Open <http://localhost:8000/docs> → screenshots **04**, **05**.

Image size guidance: 1600×1000 PNG, ≤ 400 KB. Keep the dark/light mode
consistent across the set.
