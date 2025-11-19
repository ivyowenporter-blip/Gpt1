# AI Session Console

This project exposes a minimal backend + frontend that lets you orchestrate live AI sessions, stream conversation logs, and preview browser automation output.

## Features

- REST endpoints to start, stop, and send commands to a session.
- WebSocket channel for real-time log streaming.
- Chat-like UI that separates user, AI, browser, and system events.
- Render panel capable of showing HTML snippets or mock screenshots.

## Running locally

The application uses only built-in Node.js APIs (no external dependencies). Start it with:

```bash
node server.js
```

The server listens on `http://localhost:3000`. Open that address in a browser to access the UI.

## Available endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| POST | `/api/session/start` | Creates a new session and returns its ID. |
| POST | `/api/session/:id/stop` | Stops an active session and logs the shutdown. |
| POST | `/api/session/:id/command` | Sends a command to the session; simulated AI and browser logs are emitted. |

A WebSocket is exposed at `ws://localhost:3000/ws` for real-time updates.
