#!/usr/bin/env bash
# 回归测试：校验脚本对示例文件的预期结果。任何一项不符即失败。
set -u
cd "$(dirname "$0")/.."
V="python3 scripts/validate_prompt.py"
fail=0
check() { # name, condition-expression-result(0/1), detail
  if [ "$2" -eq 0 ]; then echo "PASS $1"; else echo "FAIL $1 — $3"; fail=1; fi
}

out=$($V examples/example-01-kitchen-keys.prompt.md); rc=$?
check "example-01 exits 0" $rc "$out"
echo "$out" | grep -q "0 error(s), 0 warning(s)"; check "example-01 clean" $? "$(echo "$out" | tail -1)"

out=$($V examples/example-02-lens-B-haneke.prompt.md); rc=$?
check "lens-B exits 0" $rc "$out"
echo "$out" | grep -q "0 error(s), 1 warning(s)"; check "lens-B exactly W11" $? "$(echo "$out" | grep -E 'WARN|==')"
echo "$out" | grep -q "W11"; check "lens-B W11 present" $? ""

out=$($V examples/example-03-yogurt-comedy.prompt.md); rc=$?
check "example-03 exits 0" $rc "$out"
echo "$out" | grep -q "0 error(s), 0 warning(s)"; check "example-03 clean" $? "$(echo "$out" | tail -1)"

out=$($V examples/example-04-parameters-fight.prompt.md); rc=$?
check "example-04 exits 0" $rc "$out"
echo "$out" | grep -q "0 error(s), 1 warning(s)"; check "example-04 exactly W11" $? "$(echo "$out" | grep -E 'WARN|==')"

out=$($V examples/bad-example.prompt.md); rc=$?
[ $rc -eq 1 ]; check "bad-1 exits 1" $? "rc=$rc"
for code in E01 E12 E05 E02 E03 E04 W06 W09 W10 W02; do
  echo "$out" | grep -q "$code"; check "bad-1 has $code" $? ""
done

out=$($V examples/bad-example-2.prompt.md)
for code in W13 W15 W17; do
  echo "$out" | grep -q "$code"; check "bad-2 has $code" $? ""
done

# 2.3: these are varying states and reusable body cues, not prohibited copying.
echo "$out" | grep -q 'W14\|W18'; rc=$?
[ "$rc" -ne 0 ]; check "body-part reuse no longer emits W14/W18" $? "$out"

tmp=$(mktemp -d); cp examples/example-02-lens-B-haneke.prompt.md "$tmp/clip02.prompt.md"
out=$($V examples/example-02-lens-B-haneke.prompt.md "$tmp/clip02.prompt.md")
echo "$out" | grep -q "W16"; check "multi-file W16" $? ""
rm -rf "$tmp"

C="python3 scripts/validate_concept.py"
out=$($C examples/good-concept.md); rc=$?
check "good-concept exits 0" $rc "$out"
out=$($C examples/bad-concept.md); rc=$?
[ $rc -eq 1 ]; check "bad-concept exits 1" $? "rc=$rc"
for code in C03 C04 C05 C07; do
  echo "$out" | grep -q "$code"; check "bad-concept has $code" $? ""
done
grep -q "^## 工作示例\|^## 附：骰子" references/concept-generation.md && { echo "FAIL concept-generation.md 仍含工作示例正文"; fail=1; } || echo "PASS concept-generation.md has no worked examples"

# 结构：保留已安装的调用名称（目录大小写可以不同）
grep -q "^name: film-seedance-director" SKILL.md; check "SKILL.md invocation name preserved" $? ""
# 所有 SKILL.md 引用的 references/templates 文件存在
missing=""
for f in $(grep -oE '`(references|templates|scripts|examples)/[^`]+`' SKILL.md | tr -d '`' | sort -u); do
  [ -e "$f" ] || missing="$missing $f"
done
[ -z "$missing" ]; check "SKILL.md links resolve" $? "$missing"

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_*.py' -v
check "performance regression suite" $? ""
exit $fail
