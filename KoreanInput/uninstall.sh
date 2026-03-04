#!/bin/bash
echo "=== 한글 입력기 제거 ==="

# 실행 중인 프로세스 종료
pkill -f "korean_input.py" 2>/dev/null && echo "실행 중인 프로그램 종료됨" || true

# 파일 삭제
rm -f ~/.local/bin/korean_input.py
rm -f ~/.local/share/applications/korean-input.desktop
rm -f ~/.config/autostart/korean-input.desktop

# 현재 폴더 파일도 삭제할지 물어보기
read -p "현재 폴더(KoreanInput)도 삭제할까요? [y/N] " answer
if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
    rm -rf "$(dirname "$0")"
    echo "폴더 삭제됨"
fi

echo "=== 제거 완료! ==="
