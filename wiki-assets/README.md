# Wiki.js embedded assets

1. Create a Wiki.js page at path `/submit` using the **HTML** editor.
2. Paste the contents of `submit-form.html` (or host the file and iframe it).
3. Replace `SMARTWIKI_CONFIG` at the top of `submit-form.html` with your URLs and **ORGANIZER_API_KEY** (treat this like a secret; prefer same-origin reverse proxy that injects the header server-side in production).
4. Under **Administration → Theme → Code Injection**, add:
   - **Head**: `<link rel="stylesheet" href="https://YOUR_CDN_OR_ORIGIN/chat-widget.css" />` (or inline CSS)
   - **Body**: `<script src="https://YOUR_CDN_OR_ORIGIN/chat-widget.js"></script>` before `</body>`
5. Edit `chat-widget.js` `SMARTWIKI_CHAT_CONFIG` with `chatbotUrl` and `chatbotApiKey`.

For production, serve these static files from your reverse proxy or object storage with tight cache headers.
