#!/bin/bash

# Parse command-line arguments using heuristic rules and output as JSON

# Store all arguments in an array
args=("$@")

# Initialize arrays (using parallel arrays for key-value pairs)
arguments=()
kw_keys=()
kw_values=()

# Parse arguments
i=0
while [ $i -lt ${#args[@]} ]; do
  arg="${args[$i]}"

  if [[ $arg == -* ]]; then
    # It's an option
    option_name="${arg#"${arg%%[!-]*}"}"

    if [ $((i + 1)) -ge ${#args[@]} ] || [[ ${args[$((i + 1))]} == -* ]]; then
      # Boolean flag
      kw_keys+=("$option_name")
      kw_values+=("true")
    else
      # Option with value
      kw_keys+=("$option_name")
      kw_values+=("${args[$((i + 1))]}")
      i=$((i + 1))  # Consume the value
    fi
  else
    # Positional argument
    arguments+=("$arg")
  fi

  i=$((i + 1))
done

# Function to escape JSON string (basic: escape quotes)
escape_json() {
  echo "$1" | sed 's/"/\\"/g'
}

# Output JSON
cat <<EOF
{
  "arguments": [
EOF

first=true
for arg in "${arguments[@]}"; do
  if [ "$first" = false ]; then
    echo "    ,"
  fi
  escaped_arg=$(escape_json "$arg")
  echo "    \"$escaped_arg\""
  first=false
done

cat <<EOF
  ],
  "keyword_arguments": {
EOF

# Build unique keys list and track processed keys
declare -a processed_keys
first=true

for idx in "${!kw_keys[@]}"; do
  key="${kw_keys[$idx]}"

  # Check if this key has already been processed
  already_processed=false
  for pk in "${processed_keys[@]}"; do
    if [ "$pk" = "$key" ]; then
      already_processed=true
      break
    fi
  done

  if [ "$already_processed" = true ]; then
    continue
  fi

  # Mark this key as processed
  processed_keys+=("$key")

  # Collect all values for this key
  declare -a values_for_key
  for idx2 in "${!kw_keys[@]}"; do
    if [ "${kw_keys[$idx2]}" = "$key" ]; then
      values_for_key+=("${kw_values[$idx2]}")
    fi
  done

  # Output separator
  if [ "$first" = false ]; then
    echo "    ,"
  fi

  # If only one value, output as string; if multiple, output as array
  if [ ${#values_for_key[@]} -eq 1 ]; then
    val="${values_for_key[0]}"
    if [[ "$val" == "true" ]]; then
      echo "    \"$key\": true"
    else
      escaped_val=$(escape_json "$val")
      echo "    \"$key\": \"$escaped_val\""
    fi
  else
    # Multiple values - output as array
    echo "    \"$key\": ["
    val_first=true
    for val in "${values_for_key[@]}"; do
      if [ "$val_first" = false ]; then
        echo "      ,"
      fi
      if [[ "$val" == "true" ]]; then
        echo "      true"
      else
        escaped_val=$(escape_json "$val")
        echo "      \"$escaped_val\""
      fi
      val_first=false
    done
    echo "    ]"
  fi

  first=false
  unset values_for_key
done

cat <<EOF
  }
}
EOF