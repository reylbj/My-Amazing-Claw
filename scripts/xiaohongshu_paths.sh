#!/usr/bin/env bash

xhs_resolve_home() {
  local workspace_dir="$1"

  if [[ -n "${XHS_HOME:-}" ]]; then
    echo "${XHS_HOME}"
    return 0
  fi

  local candidates=(
    "${workspace_dir}/skills/xiaohongshu-send"
    "${workspace_dir}/xiaohongshu-send"
  )

  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -d "${candidate}" ]]; then
      echo "${candidate}"
      return 0
    fi
  done

  echo "${workspace_dir}/skills/xiaohongshu-send"
}

xhs_resolve_note_skill_dir() {
  local workspace_dir="$1"

  if [[ -n "${XHS_NOTE_HOME:-}" ]]; then
    echo "${XHS_NOTE_HOME}"
    return 0
  fi

  local candidates=(
    "${workspace_dir}/skills/小红书笔记技能包"
    "${workspace_dir}/小红书笔记技能包"
  )

  local candidate
  for candidate in "${candidates[@]}"; do
    if [[ -d "${candidate}" ]]; then
      echo "${candidate}"
      return 0
    fi
  done

  echo "${workspace_dir}/skills/小红书笔记技能包"
}
