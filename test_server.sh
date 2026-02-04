#!/bin/bash

# Simple bash script for testing the Claude Code SDK Server using curl
# No Python dependencies required!

BASE_URL="http://localhost:3000"

echo "=========================================="
echo "Claude Code SDK Server - Curl Test Script"
echo "=========================================="

# 1. Health Check
echo -e "\n1️⃣  Health Check"
echo "------------------------------------------"
curl -s "$BASE_URL/health" | jq '.'

# 2. Simple Query
echo -e "\n2️⃣  Simple Query"
echo "------------------------------------------"
curl -s -X POST "$BASE_URL/query" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is 2 + 2? Answer in one word.",
    "stream": false
  }' | jq '.response'

# 3. Start Session
echo -e "\n3️⃣  Start Conversation Session"
echo "------------------------------------------"
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/session/start" \
  -H "Content-Type: application/json" \
  -d '{
    "initial_prompt": "What is the capital of France?"
  }')

echo "$SESSION_RESPONSE" | jq '.'
SESSION_ID=$(echo "$SESSION_RESPONSE" | jq -r '.session_id')

# 4. Continue Conversation
echo -e "\n4️⃣  Continue Conversation (Remembers Context)"
echo "------------------------------------------"
curl -s -X POST "$BASE_URL/session/$SESSION_ID/query" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What is the population of that city?"
  }' | jq '.response'

# 5. List Sessions
echo -e "\n5️⃣  List Active Sessions"
echo "------------------------------------------"
curl -s "$BASE_URL/sessions" | jq '.'

# 6. Close Session
echo -e "\n6️⃣  Close Session"
echo "------------------------------------------"
curl -s -X DELETE "$BASE_URL/session/$SESSION_ID" | jq '.'

echo -e "\n=========================================="
echo "✓ Test complete!"
echo "=========================================="
