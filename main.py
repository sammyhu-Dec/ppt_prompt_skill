import argparse
from pathlib import Path

import config
from app.pipeline.skill_pipeline import run_skill_pipeline


def parse_args():
    parser = argparse.ArgumentParser(description="PPT -> Storyboard Prompt Skill Demo v1")
    parser.add_argument("--input", "-i", required=True, help="输入 PPTX 文件路径")
    parser.add_argument("--output", "-o", default=config.OUTPUT_DIR, help="输出目录，默认 output")
    parser.add_argument(
        "--provider",
        choices=["mock", "openai"],
        default=config.LLM_PROVIDER,
        help="LLM 提供方。mock 用于无 API Key 演示；openai 调用真实模型。",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    pptx_path = Path(args.input)
    output_dir = Path(args.output)

    if not pptx_path.exists():
        raise FileNotFoundError(f"找不到输入文件：{pptx_path}")

    result = run_skill_pipeline(
        pptx_path=pptx_path,
        output_dir=output_dir,
        provider=args.provider,
    )

    print("\n✅ Skill Demo 运行完成")
    print(f"输出目录：{output_dir.resolve()}")
    print("生成文件：")
    for file_path in result["files"]:
        print(f"- {file_path}")


if __name__ == "__main__":
    main()
