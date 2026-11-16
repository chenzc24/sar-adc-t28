# 版图查询说明

查询 OA 时优先复用 virtuoso bridge 的连接、批量属性读取和几何解析。项目检查只保留对象筛选与判定条件；遇到现有接口不能表达的查询，再用一小段 SKILL 调用 Virtuoso 数据库 API。重复出现的相同查询才考虑收进 bridge。

## 已有入口

| 入口 | 参数 | 返回内容 |
| --- | --- | --- |
| `VirtuosoClient.from_env()` | 可选 `profile`、`timeout` | 使用既有配置的客户端 |
| `client.fetch(expr, fields, timeout=30)` | 返回对象列表的 SKILL 表达式、属性名列表 | `list[dict]`，每个对象一行 |
| `client.fetch_one(expr, fields, timeout=30)` | 返回单个对象的表达式、属性名列表 | `dict` |
| `layout_read_geometry(lib, cell, view="layout")` | 库、cell、view | 待执行的 SKILL 字符串 |
| `client.execute_skill(code, timeout=30)` | SKILL 代码 | `VirtuosoResult`，包含 `status`、`output`、`errors`、`warnings`、`metadata` |
| `parse_layout_geometry_output(raw)` | 几何读取的 `output` | 图形和实例的 `list[dict]` |

`fetch` 自动批量取属性并解析结果：字符串去引号，`nil` 为 `None`，`t` 为 `True`，列表为 Python 列表；数字目前保留为字符串，计算时显式转换。当前实现没有向调用方完整传递执行状态，空列表不能单独证明“对象不存在”；异常空结果须用 `execute_skill()` 检查同一查询的状态及错误。

几何读取当前包含本层图形和实例，不递归展开子 cell，也不完整包含 pin、via、mosaic 或网络属性。图形项含 `objType/layer/purpose/bbox/points/xy/orient/text`，实例项含 `name/lib/cell/view/xy/orient/bbox/transform`；适用的 `bbox/points/xy` 被解析为数值坐标，`transform` 仍为原始文本。现有数值解析器不支持科学计数法，遇到此类输出应保留原始值并修正已有解析器。

## 连接和查询对象

使用已经配置好的 bridge Python 环境与 profile。以下示例查询 Virtuoso **当前编辑的 layout**，可能包含未保存修改；开始前打开目标 view，并保持查询期间的编辑上下文不变。

```python
from virtuoso_bridge import ExecutionStatus, VirtuosoClient
from virtuoso_bridge.virtuoso.layout import (
    layout_read_geometry,
    parse_layout_geometry_output,
)

client = VirtuosoClient.from_env()
lib, cell, view = client.get_current_design()
if not lib or not cell or view != "layout":
    raise RuntimeError("请先在 Virtuoso 中打开目标 layout")
print({"library": lib, "cell": cell, "view": view, "source": "session"})
```

实例、引脚名称和图形的简短查询：

```python
instances = client.fetch(
    "geGetEditCellView()~>instances",
    ["name", "libName", "cellName", "viewName", "xy", "orient", "bBox"],
)
terminals = client.fetch(
    "geGetEditCellView()~>terminals", ["name", "direction"],
)
metal = client.fetch(
    'setof(s geGetEditCellView()~>shapes '
    'equal(s~>lpp list("M4" "drawing")))',
    ["objType", "lpp", "bBox", "points"],
)
```

`instances` 是当前层的实例列表，`terminals` 是当前 cell 的端口列表，`metal` 是当前 cell 自身的 M4 drawing 图形。子实例内部的图形需查询其 master；端口名本身不包含引脚几何。

需要现成的图形和实例解析结果时：

```python
result = client.execute_skill(layout_read_geometry(lib, cell, view=view), timeout=30)
if result.status != ExecutionStatus.SUCCESS:
    raise RuntimeError(result.errors)
geometry = parse_layout_geometry_output(result.output or "")
if any(obj["kind"].startswith("ERROR") for obj in geometry):
    raise RuntimeError(result.output)
```

这个入口按名称打开数据库。在同一 Virtuoso 会话中，按名打开也可能取得已在内存中的 view，不能将其自动视为独立的磁盘快照。查询已保存 OA 时使用现有隔离的后台读取流程，并记录其输入身份。当前本地版本的几何读取函数还存在 cellview 引用释放缺口；长期批量使用前应复用上游修复，避免另写打开/关闭逻辑。

## 实例引脚和坐标变换

在当前 layout 中选中一个普通实例。下面通过其实际 master 读取所有引脚图形，并用实例变换将包围盒转换到所在父 cell 坐标；此遍历方式也用于项目的 `design/mom.il`。

```python
result = client.execute_skill('''
let((inst rows)
  inst = car(geGetSelSet())
  unless(inst && inst~>objType == "inst"
    error("Select one ordinary instance first"))
  foreach(term inst~>master~>terminals
    foreach(pin term~>pins
      foreach(fig pin~>figs
        rows = cons(list(inst~>name term~>name fig~>lpp
          dbTransformBBox(fig~>bBox inst~>transform)) rows))))
  reverse(rows)
)
''', timeout=30)
if result.status != ExecutionStatus.SUCCESS:
    raise RuntimeError(result.errors)
print(result.output)
```

`output` 是 SKILL 列表文本，每行记录的顺序为 `(实例名 端口名 layer/purpose 父坐标包围盒)`；本例用于检查，不另写解析器。`dbTransformBBox()` 处理实例的平移、旋转和镜像；转换点用 `dbTransformPoint()`。多层路径需要逐层组合变换；父 cell 坐标只有在父 cell 就是顶层时才是顶层坐标。查询原始引脚几何，避免用生成器中的固定偏移量代替实际 pin。

## 检查结果怎样使用

- 记录库、cell、view、来源（当前会话或已保存 OA）、层级路径和坐标单位；数值以当前技术库的用户单位为准。
- 包围盒用于定位和筛选。多边形接触、OA 网络属性和 LVS 连通性结论分别报告；短路判定需要真实图形及跨层连接规则，寄生数值使用对应版本的 PEX。
- 连接、传输、打开数据库和输出解析优先使用 bridge 或项目已有执行器。临时查询及结果放在忽略的 `work/layout/`；可复用用法维护在本页。

本页接口按本地 `virtuoso-bridge-lite` 源码核对。Python 示例可作静态语法检查；未运行于目标 Virtuoso 的示例不能视为 OA 检查证据。
