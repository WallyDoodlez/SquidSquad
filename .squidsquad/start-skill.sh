#!/bin/bash
cd "$(git rev-parse --show-toplevel)"
claude --permission-mode auto --enable-auto-mode -p "$(cat .squidsquad/skill/CLAUDE.md)"
