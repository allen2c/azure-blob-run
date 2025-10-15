#!/bin/bash

# Parse command-line arguments using heuristic rules and output as JSON

# Store all arguments in an array
args=("$@")

# Initialize arrays and associative array
arguments=()
declare -A keyword_arguments

# Parse arguments
i=0
while [ $i -lt ${#args[@]} ]; do
  arg="${args[$i]}"

  if [[ $arg == -* ]]; then
    # It's an option
    option_name=$(echo "$arg" | sed 's/^-*//')

    if [ $((i + 1)) -ge ${#args[@]} ] || [[ ${args[$((i + 1))]} == -* ]]; then
      # Boolean flag
      keyword_arguments["$option_name"]="true"
    else
      # Option with value
      keyword_arguments["$option_name"]="${args[$((i + 1))]}"
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

first=true
for key in "${!keyword_arguments[@]}"; do
  if [ "$first" = false ]; then
    echo "    ,"
  fi
  val="${keyword_arguments[$key]}"
  if [[ "$val" == "true" ]]; then
    echo "    \"$key\": true"
  else
    escaped_val=$(escape_json "$val")
    echo "    \"$key\": \"$escaped_val\""
  fi
  first=false
done

cat <<EOF
  }
}
EOF