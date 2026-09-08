#!/usr/bin/env bash

set -o pipefail

INPUT_DIR="${1:-.}"
OUTPUT_FILE="${2:-llm_bundle.txt}"

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------

SCRIPT_PATH="$(
  realpath "$0" 2>/dev/null ||
  python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$0"
)"

OUTPUT_PATH="$(
  realpath "$OUTPUT_FILE" 2>/dev/null ||
  python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$OUTPUT_FILE"
)"

# Make INPUT_DIR absolute.
INPUT_DIR="$(
  realpath "$INPUT_DIR" 2>/dev/null ||
  python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$INPUT_DIR"
)"

if [[ ! -d "$INPUT_DIR" ]]; then
  echo "Error: input directory does not exist: $INPUT_DIR" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Module selection
#
# Controls:
#   1-9       Toggle module immediately
#   10+       Type the full number, then press Enter
#   a         Select all
#   n         Select none
#   q         Quit
#   Enter     Continue
#   Backspace Remove last digit while entering a multi-digit number
# ---------------------------------------------------------------------------

SELECTED_MODULES=()

select_modules() {
  local modules=()
  local module
  local i
  local choice
  local number_buffer=""

  # "." represents root-level files.
  modules+=(".")

  # First-level directories are modules.
  while IFS= read -r -d '' module; do
    modules+=("$module")
  done < <(
    find "$INPUT_DIR" \
      -mindepth 1 \
      -maxdepth 1 \
      -type d \
      ! -name ".git" \
      ! -name "target" \
      -print0 |
    sort -z
  )

  # Select everything by default.
  local selected=()

  for ((i = 0; i < ${#modules[@]}; i++)); do
    selected[i]=1
  done

  while true; do
    clear

    echo "=========================================="
    echo "       Select modules to include"
    echo "=========================================="
    echo
    echo "  a) Select all"
    echo "  n) Select none"
    echo "  q) Quit"
    echo "  Enter) Continue"
    echo
    echo "  Press 1-9 to toggle immediately."
    echo "  For 10+, type the number then Enter."
    echo
    echo "------------------------------------------"

    for ((i = 0; i < ${#modules[@]}; i++)); do
      local display_name

      if [[ "${modules[i]}" == "." ]]; then
        display_name="(root files)"
      else
        display_name="${modules[i]#$INPUT_DIR/}"
      fi

      if [[ "${selected[i]}" -eq 1 ]]; then
        printf '  [x] %2d) %s\n' "$((i + 1))" "$display_name"
      else
        printf '  [ ] %2d) %s\n' "$((i + 1))" "$display_name"
      fi
    done

    echo "------------------------------------------"

    if [[ -n "$number_buffer" ]]; then
      printf "  Number: %s" "$number_buffer"
    else
      printf "  Press key: "
    fi

    # Read one key immediately without requiring Enter.
    IFS= read -rsn1 choice

    # -----------------------------------------------------------------------
    # Enter
    # -----------------------------------------------------------------------

    if [[ "$choice" == "" ]]; then

      # If a multi-digit number is pending, apply it.
      if [[ -n "$number_buffer" ]]; then
        if [[ "$number_buffer" =~ ^[0-9]+$ ]]; then
          i=$((10#$number_buffer - 1))

          if (( i >= 0 && i < ${#modules[@]} )); then
            if [[ "${selected[i]}" -eq 1 ]]; then
              selected[i]=0
            else
              selected[i]=1
            fi
          fi
        fi

        number_buffer=""
        continue
      fi

      # No number pending: continue.
      break
    fi

    # -----------------------------------------------------------------------
    # Backspace
    # -----------------------------------------------------------------------

    if [[ "$choice" == $'\x7f' || "$choice" == $'\b' ]]; then
      if [[ -n "$number_buffer" ]]; then
        number_buffer="${number_buffer%?}"
      fi
      continue
    fi

    # -----------------------------------------------------------------------
    # Number keys
    # -----------------------------------------------------------------------

    if [[ "$choice" =~ ^[0-9]$ ]]; then

      # If there are fewer than 10 modules, every number can be
      # handled immediately.
      if (( ${#modules[@]} < 10 )); then

        # Ignore 0.
        if [[ "$choice" == "0" ]]; then
          continue
        fi

        i=$((10#$choice - 1))

        if (( i >= 0 && i < ${#modules[@]} )); then
          if [[ "${selected[i]}" -eq 1 ]]; then
            selected[i]=0
          else
            selected[i]=1
          fi
        fi

        continue
      fi

      # For 10+ modules:
      #
      #   1 + Enter  -> module 1
      #   1 2 + Enter -> module 12
      #
      # This avoids ambiguity between 1 and 10+.
      number_buffer+="$choice"

      continue
    fi

    # -----------------------------------------------------------------------
    # If a command key is pressed while a number is pending,
    # finalize the number first.
    # -----------------------------------------------------------------------

    if [[ -n "$number_buffer" ]]; then
      if [[ "$number_buffer" =~ ^[0-9]+$ ]]; then
        i=$((10#$number_buffer - 1))

        if (( i >= 0 && i < ${#modules[@]} )); then
          if [[ "${selected[i]}" -eq 1 ]]; then
            selected[i]=0
          else
            selected[i]=1
          fi
        fi
      fi

      number_buffer=""
    fi

    # -----------------------------------------------------------------------
    # Commands
    # -----------------------------------------------------------------------

    case "$choice" in
      a|A)
        for ((i = 0; i < ${#modules[@]}; i++)); do
          selected[i]=1
        done
        ;;

      n|N)
        for ((i = 0; i < ${#modules[@]}; i++)); do
          selected[i]=0
        done
        ;;

      q|Q)
        clear
        echo
        echo "Cancelled."
        exit 0
        ;;

      *)
        # Ignore unsupported keys.
        ;;
    esac
  done

  SELECTED_MODULES=()

  for ((i = 0; i < ${#modules[@]}; i++)); do
    if [[ "${selected[i]}" -eq 1 ]]; then
      SELECTED_MODULES+=("${modules[i]}")
    fi
  done

  if [[ ${#SELECTED_MODULES[@]} -eq 0 ]]; then
    echo
    echo "No modules selected."
    exit 0
  fi
}

# ---------------------------------------------------------------------------
# Censor values in dotenv files while preserving variable names.
# ---------------------------------------------------------------------------

censor_env_file() {
  python3 -c '
import re
import sys

for line in sys.stdin:
    # Preserve comments and blank lines.
    if re.match(r"^\s*(#|$)", line):
        sys.stdout.write(line)
        continue

    # Match:
    #   KEY=value
    #   KEY = value
    #   export KEY=value
    match = re.match(
        r"^(\s*(?:export\s+)?[A-Za-z_][A-Za-z0-9_]*\s*=).*$",
        line
    )

    if match:
        newline = "\n" if line.endswith("\n") else ""
        sys.stdout.write(
            match.group(1) + "***REDACTED***" + newline
        )
    else:
        # Leave unrecognized dotenv lines unchanged.
        sys.stdout.write(line)
'
}

# ---------------------------------------------------------------------------
# Detect dotenv files
#
# Examples:
#   .env
#   .env.local
#   .env.production
#   config.env
#   anything.env
# ---------------------------------------------------------------------------

is_env_file() {
  local filename

  filename="$(basename "$1")"

  case "$filename" in
    .env|.env.*|*.env)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

# ---------------------------------------------------------------------------
# Check whether a MIME type should be included.
# ---------------------------------------------------------------------------

is_supported_mime() {
  local mime="$1"

  case "$mime" in
    text/*)
      return 0
      ;;

    application/json)
      return 0
      ;;

    application/javascript)
      return 0
      ;;

    application/x-javascript)
      return 0
      ;;

    application/xml)
      return 0
      ;;

    application/yaml)
      return 0
      ;;

    application/x-yaml)
      return 0
      ;;

    unknown)
      return 0
      ;;

    *)
      return 1
      ;;
  esac
}

# ---------------------------------------------------------------------------
# Select modules BEFORE creating the output file.
# ---------------------------------------------------------------------------

select_modules

# ---------------------------------------------------------------------------
# Create output file
# ---------------------------------------------------------------------------

cat > "$OUTPUT_FILE" <<'EOF'
Repository bundle for LLM analysis.
Each file is wrapped with <FILE_START> and <FILE_END>.
Use PATH to identify file location.
Treat file contents as raw source text.

EOF

# ---------------------------------------------------------------------------
# Process selected modules
# ---------------------------------------------------------------------------

for module in "${SELECTED_MODULES[@]}"; do

  # "." means root-level files only.
  if [[ "$module" == "." ]]; then
    SEARCH_ROOT="$INPUT_DIR"
    FIND_DEPTH_ARGS=(-maxdepth 1)
  else
    SEARCH_ROOT="$module"
    FIND_DEPTH_ARGS=()
  fi

  find "$SEARCH_ROOT" \
    "${FIND_DEPTH_ARGS[@]}" \
    \( -type d -name ".git" -prune \) -o \
    \( -type d -name "target" -prune \) -o \
    \( -type f \( -name "*.class" -o -name "*.md" \) -print0 \) -o \
    \( -type f -print0 \) |
  while IFS= read -r -d '' file; do

    # ---------------------------------------------------------------
    # Skip excluded extensions.
    # ---------------------------------------------------------------

    case "$file" in
      *.class|*.md)
        continue
        ;;
    esac

    # ---------------------------------------------------------------
    # Resolve file path.
    # ---------------------------------------------------------------

    FILE_PATH="$(
      realpath "$file" 2>/dev/null ||
      python3 -c \
        'import os,sys; print(os.path.realpath(sys.argv[1]))' \
        "$file"
    )"

    # ---------------------------------------------------------------
    # Skip:
    #   - This script
    #   - Any file named combine.sh
    #   - Configured output file
    #   - Any file named llm_bundle.txt
    # ---------------------------------------------------------------

    if [[ "$FILE_PATH" == "$SCRIPT_PATH" ]] ||
       [[ "$(basename "$FILE_PATH")" == "combine.sh" ]] ||
       [[ "$FILE_PATH" == "$OUTPUT_PATH" ]] ||
       [[ "$(basename "$FILE_PATH")" == "llm_bundle.txt" ]]; then
      continue
    fi

    # ---------------------------------------------------------------
    # Determine MIME type.
    # ---------------------------------------------------------------

    MIME_TYPE="$(
      file --brief --mime-type "$file" 2>/dev/null ||
      echo unknown
    )"

    # ---------------------------------------------------------------
    # Skip binary files.
    # ---------------------------------------------------------------

    if ! is_supported_mime "$MIME_TYPE"; then
      continue
    fi

    # ---------------------------------------------------------------
    # Append file to bundle.
    # ---------------------------------------------------------------

    {
      echo "<FILE_START>"
      echo "PATH: $file"
      echo "MIME: $MIME_TYPE"
      echo "CONTENT:"

      if is_env_file "$file"; then
        echo "[ENV FILE — VALUES CENSORED]"
        censor_env_file < "$file"
      else
        cat "$file"
      fi

      echo
      echo "<FILE_END>"
      echo

    } >> "$OUTPUT_FILE"

  done
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo
echo "=========================================="
echo "Bundle complete"
echo "=========================================="
echo "Output: $OUTPUT_FILE"
echo
echo "Selected modules:"

for module in "${SELECTED_MODULES[@]}"; do
  if [[ "$module" == "." ]]; then
    echo "  - (root files)"
  else
    echo "  - ${module#$INPUT_DIR/}"
  fi
done

echo
echo "Done."