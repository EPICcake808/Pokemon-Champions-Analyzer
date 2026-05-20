FROM node:22-bookworm-slim

ENV NEXT_TELEMETRY_DISABLED=1 \
    POKEMON_ANALYZER_REPO_ROOT=/app

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY pokemon_team_analyzer ./pokemon_team_analyzer
COPY examples ./examples

RUN python3 -m pip install --no-cache-dir .

WORKDIR /app/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web ./

RUN npm run build

ENV NODE_ENV=production

EXPOSE 3000

CMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3000"]