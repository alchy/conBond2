#!/bin/bash
# VLASTNÍ instance UDPipe 2. Nic mimo tenhle adresář nepotřebuje: zdrojáky
# jsou ve vendor/, model v models/, interpret a knihovny v .venv/.
#
#   ./udpipe.sh              # start na portu 8020
#   PORT=9000 ./udpipe.sh    # jiný port
#
# Model je TÝŽ, ze kterého vznikla výchozí data (cs_all-ud-2.17-251125),
# a to je podstatné: rozbor nové věty pak vrací aktivace, které v poli už
# mají svou vertikálu, takže nová věta nezaloží sloupec navíc.
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/vendor/udpipe2-src"
MODEL="$ROOT/models/udpipe2/cs_all-ud-2.17-251125.model"
PY="$ROOT/.venv/bin/python"
# Port se bere z config.json, ne z čísla natvrdo. Proměnná PORT ho přebije
# (tak ho předává server/processes.py); poslední záchrana je 9010.
PORT="${PORT:-$(python3 - "$ROOT/config.json" <<'EOF' 2>/dev/null || echo 9010
import json, sys
try:
    print(json.load(open(sys.argv[1]))["udpipe_port"])
except Exception:
    print(9010)
EOF
)}"

# Rozbor je jediné opravdu drahé místo a škáluje s jádry. Dvě necháváme
# systému, ať stroj při rozboru nezamrzne.
JADRA="$( (sysctl -n hw.logicalcpu 2>/dev/null || nproc) 2>/dev/null || echo 4 )"
THREADS="${THREADS:-$(( JADRA > 4 ? JADRA - 2 : 2 ))}"

# model UDPipe 2 je ADRESÁŘ (váhy + tokenizery), proto -e a ne -f
[ -e "$MODEL" ] || { echo "chybí model: $MODEL"; exit 1; }
[ -x "$PY" ]    || { echo "chybí .venv — vytvoř ho podle README"; exit 1; }

# UDPipe 2 nepočítá jen ze svých vah: pro embeddingy si sahá na RobeCzech
# přes HuggingFace. Bez tohohle by si ho stáhl do ~/.cache a při prvním
# spuštění bez sítě by spadl — tedy přesně ta závislost na okolí, které se
# zbavujeme. Cache proto míří dovnitř projektu a režim je natvrdo offline,
# ať se případná chybějící váha ohlásí hned a ne tichým stahováním.
export HF_HOME="$ROOT/models/hf"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
[ -d "$HF_HOME/hub/models--ufal--robeczech-base" ] || {
  echo "chybí embedding model RobeCzech v $HF_HOME"; exit 1; }

cd "$SRC"
echo "UDPipe: port $PORT, vláken $THREADS (jader $JADRA)"
exec "$PY" udpipe2_server.py "$PORT" --threads="$THREADS" \
  czech \
  czech-pdtc-ud-2.17-251125:cs_pdtc-ud-2.17-251125:cs:ces:cze \
  "$MODEL" cs_pdtc \
  https://ufal.mff.cuni.cz/udpipe/2/models
