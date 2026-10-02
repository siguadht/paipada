"""第二空间一次性局部重绘验证，默认只离线检查，不提交云任务。"""

import argparse

from scripts.prepare_livingroom_inpaint import OUTPUT, prepare
from scripts.qa_bedroom_inpaint import poll_existing, submit_once, validate_inputs, visual_client


PROMPT = (
    "保持原照片机位、大窗、窗帘、吊顶与墙体。只在白色选区布置写实的现代原木客厅："
    "左墙前放浅米色沙发，前方摆木质茶几、浅色地毯和一盆绿植。清理地面杂物，光影自然。黑色区域保持原样。"
)
MARKER = OUTPUT / "submission.json"
RESULT_NAME = "客厅-即梦遮罩单次结果.jpg"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--submit-once", action="store_true", help="创建一项可能计费的任务；须单独授权")
    group.add_argument("--poll", action="store_true", help="只查询已经提交的任务")
    args = parser.parse_args()
    photo_path, mask_path = prepare()
    validate_inputs(photo_path, mask_path, PROMPT)
    if not args.submit_once and not args.poll:
        print("第二空间本地输入合规；没有调用云接口")
        return
    client = visual_client()
    if args.submit_once:
        print(f"任务 ID：{submit_once(client, photo_path, mask_path, MARKER, PROMPT)}")
    else:
        print(f"结果：{poll_existing(client, MARKER, OUTPUT, RESULT_NAME)}")


if __name__ == "__main__":
    main()
