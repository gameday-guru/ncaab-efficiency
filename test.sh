#!/bin/bash
curl -X POST http://localhost:8000/method/get_bracket_by_round \
    -H 'Content-Type: application/json' \
   -d '{"id" : 1}'