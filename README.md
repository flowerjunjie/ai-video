# ai-video · 用AI讲古 短视频生成系统

零成本、无 GPU、开源的短视频生成工具链 + MCP server。
把「东方智慧(释道儒/王阳明) × 未来智能(AI 觉醒)」翻译成 AI 时代生存算法,
自动产出可直接开播的 9:16 竖屏成片 + 封面。

## 链路
```
选题 → [AGNES/Anthropic 自动写脚本, 无 key 走离线骨架]
     → edge-tts 免费配音(5 种中文音色)
     → Pexels/Pixabay 免费 B-roll(有 key) 或 霓虹网格 fallback(无 key)
     → ffmpeg 合成(拼接/动态字幕/9:16/封面)
     → 半自动发布物料(标题/标签/合规/AI标注) → 平台手动上传
     → 手动导入数据回流(播放/完播/赞评转)
     → AGNES 分析回流 → 生成下一批高潜选题 → 回到写脚本   ⟲ 全自动化闭环
```
全部本地 + 免费 API,单条成片 < 2 分钟,CPU 即可。
发布与回流默认「半自动」:个人号无企业发布资质,物料一键备齐后人工上传,
数据手动复制导入即可驱动下一批选题——链路零额外成本、零 API 依赖。

## 快速开始
```bash
pip install -r requirements.txt
pip install edge-tts        # 免费 TTS

# 方式1:直接跑管线
python3 pipeline.py 01_wangyangming

# 方式2:作为 MCP server 接入任意 MCP client
python3 shortvideo_mcp.py
```

## MCP 工具
| tool | 作用 |
|------|------|
| `write_script(topic, column, tone)` | 生成完整脚本 JSON(口播/分镜/字幕/标题/封面) |
| `tts_voice(text, voice)` | 免费配音,换音色试听 |
| `compose_video(script_id)` | 一键出成片 + 封面 |
| `prepare_publish(ids, platform, schedule)` | 半自动发布物料包(标题/标签/合规/AI标注),输出可复制文案 |
| `import_metrics([...], source)` | 手动导入播放/完播/赞评转,结构化落盘 |
| `auto_next_topics(n)` | 读回流数据,AGNES 出下一批高潜选题并写回 scripts/ |
| `list_scripts()` | 查脚本库存 |

MCP 客户端配置:
```json
{"mcpServers": {"shortvideo": {"command": "python3", "args": ["<path>/shortvideo_mcp.py"]}}}
```

## 环境变量(全部可选,不配也有 fallback)
| 变量 | 作用 |
|------|------|
| `AGNES_API_KEY` / `ANTHROPIC_API_KEY` | 接 AGNES/Anthropic 自动写脚本 |
| `AGNES_BASE_URL` / `ANTHROPIC_BASE_URL` | AGNES 网关地址 |
| `SV_MODEL` | 模型名,默认 `claude-sonnet-4-6` |
| `PEXELS_API_KEY` | 拉真实 B-roll(免费 key) |
| `PIXABAY_API_KEY` | 拉真实 B-roll(免费 key) |

不配 `AGNES_API_KEY` → `write_script` 自动走离线规则骨架;
不配素材 key → `compose_video` 自动用霓虹网格画面。

## 目录
```
scripts/      脚本 JSON(分镜+口播+字幕+引文出处)
assets/       中间产物(各分镜画面/配音)
output/       成片 + 封面
pipeline.py   纯 Python 管线(不走 MCP 也能跑)
shortvideo_mcp.py  MCP server
```

## 合规红线(写进脚本引擎当护栏)
1. 理性包装,不贩卖焦虑、不做玄学承诺(禁"改命/开光/消灾")。
2. AI 生成内容在发布平台标注"内容由 AI 生成"。
3. 古语引用须核出处,不确定不写(防"一本正经编古语"翻车)。
