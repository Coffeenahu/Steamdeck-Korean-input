#!/bin/bash
echo "=== 한글 입력기 설치 ==="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.local/bin"
VENV_DIR="$HOME/korean-env"

# 1. venv 생성
echo "가상환경 생성 중..."
python3 -m venv "$VENV_DIR"

# 2. pynput 설치
echo "pynput 설치 중..."
"$VENV_DIR/bin/pip" install pynput --no-deps -q
"$VENV_DIR/bin/pip" install six python-xlib -q

# 3. pystray, pillow 설치 (트레이 아이콘용)
echo "pystray 설치 중..."
"$VENV_DIR/bin/pip" install pystray pillow -q

# 4. 프로그램 복사
echo "프로그램 설치 중..."
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/korean_input.py" "$INSTALL_DIR/korean_input.py"
chmod +x "$INSTALL_DIR/korean_input.py"

# 5. 실행 스크립트 생성 (경로 하드코딩 없이)
cat > "$INSTALL_DIR/korean_input_run.sh" << RUNEOF
#!/bin/bash
exec "$HOME/korean-env/bin/python3" "$HOME/.local/bin/korean_input.py"
RUNEOF
chmod +x "$INSTALL_DIR/korean_input_run.sh"

# 6. 바로가기 생성
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/korean-input.desktop" << DESK
[Desktop Entry]
Name=한글 입력기
Comment=두벌식 한글 입력기
Exec=bash -c "nohup $HOME/.local/bin/korean_input_run.sh &"
Icon=input-keyboard
Terminal=false
Type=Application
Categories=Utility;
DESK

# 7. 자동시작 등록
mkdir -p "$HOME/.config/autostart"
cat > "$HOME/.config/autostart/korean-input.desktop" << DESK
[Desktop Entry]
Name=한글 입력기
Exec=bash -c "sleep 3 && nohup $HOME/.local/bin/korean_input_run.sh &"
Icon=input-keyboard
Terminal=false
Type=Application
DESK

echo ""
echo "=== 설치 완료! ==="
echo "지금 바로 실행할까요? [Y/n]"
read -r answer
if [[ "$answer" != "n" && "$answer" != "N" ]]; then
    nohup "$VENV_DIR/bin/python3" "$INSTALL_DIR/korean_input.py" > /dev/null 2>&1 &
    sleep 1
    if pgrep -f "korean_input.py" > /dev/null; then
        echo "실행됨! 트레이 아이콘을 확인하세요."
    else
        echo "실행 실패. 수동으로 실행해주세요:"
        echo "  nohup ~/korean-env/bin/python3 ~/.local/bin/korean_input.py &"
    fi
fi
