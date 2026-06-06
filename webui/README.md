# EasyGS WebUI

Browser front-end for the EasyGS gateway. It is built with Vite, React,
TypeScript, Tailwind, and shadcn/ui, and talks to the EasyGS websocket channel
on the same port.

## Develop From Source

Enable the WebSocket channel in `~/.easygs/config.json`:

```json
{ "channels": { "websocket": { "enabled": true, "port": 25685 } } }
```

Start EasyGS:

```bash
easygs gateway
```

Start the WebUI dev server:

```bash
cd webui
npm install
npm run dev
```

The dev server proxies `/api`, `/webui`, and WebSocket traffic to
`http://127.0.0.1:25685`. Override that target with:

```bash
EASYGS_API_URL=http://127.0.0.1:25685 npm run dev
```

## Build

```bash
cd webui
npm run build
```

Production assets are written to `../easygs/web/dist`, which is served by
`easygs gateway` when the websocket channel is enabled.
