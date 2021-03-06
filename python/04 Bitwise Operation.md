# Bitwise Operation
操作符 | 作用
----- | -----
`&` | 按位与
<code>&#124;</code> | 按位或
`~` | 按位取反
`^` | 按位异或
`<<` | 算数左移
`>>` | 算数右移

## 奇偶判断

```python
def is_even(x):
    return x & 1 == 0
```
- 在整数的二进制表示中, 如果最后一位为 0 则为偶数, 为 1 则是奇数.

## 第 n 位是否为 1
```python
def is_nth_bit_set(x, n):
  return x & (1 << n) != 0
```
- `n` 由 0 开始.

## 将第 n 位设为 1
```python
def set_nth_bit(x, n):
    return x | 1 << n
```
- 与 0 或, 原位不变. 与 1 或, 原位为 1.
- 运算符优先级:

  算数 > 位移 > 比较 > 位 > 逻辑 > 赋值

## 将第 n 位设为 0
```python
def unset_nth_bit(x, n):
    return x & ~(1 << n)
```
- 与 1 与, 原位不变. 与 0 与, 原位为 0.
- 单目运算符优先级大于多目运算符.

## 第 n 位取反
```python
def toggle_nth_bit(x, n):
    return x ^ (1 << n)
```
- 与 0 异或, 原位不变. 与 1 异或, 原位取反.

## 将最右侧的 1 设为 0
```python
def turn_off_rightmost_1bit(x):
    return x & x - 1
```

示例:
```
    01011000    (x)
&   01010111    (x-1)
    --------
    01010000

    00000000    (x)
&   11111111    (x-1)
    --------
    00000000
```

&nbsp; |左 | 1 | 右 | 说明
--- | --- | --- | --- | ---
x | 0101 | 1 | 000 | 最右侧的 1 将二进制表示分为 3 部分
x - 1 | 0101 | 0 | 111 | 减 1 时, 右侧的 0 借位全变为 1, 1 借出一位变为 0

## 将最低位到最右侧 1 之间的所有位置 1
```python
def propagate_rightmost_1bit(x):
    return x | x - 1
```
示例:
```
    01011000    (x)
|   01010111    (x-1)
    --------
    01011111

    00000000    (x)
|   11111111    (x-1)
    --------
    11111111
```

## 找到最右侧 1 的所在位
```python
def get_rightmost_1bit(x):
    return x & -x
```
示例:
```
    01011000    (x)
&   10101000    (-x)
    --------
    00001000

    00000000    (x)
&   00000000    (-x)
    --------
    00000000
```

&nbsp; |左 | 1 | 右 | 说明
--- | --- | --- | --- | ---
x | 0101 | 1 | 000 |
-x | 1010 | 1 | 000 | 负数用补码表示, 计算分为取反和加 1 两部分
~x | 1010 | 0 | 111 |
~x + 1 | 1010 | 1 | 000 | 计算后左侧取反, 1 和右侧不变


## 找到最右侧 0 的所在位
```python
def get_rightmost_0bit(x):
    return ~x & x + 1
```
示例:
```
~   01011001    (x)
    --------    
    10100110    (~x)
&   01011010    (x+1)
    --------
    00000010

~   11111111    (x)
    --------
    00000000    (~x)
&   00000000    (x+1)
    --------
    00000000
```

&nbsp; |左 | 0 | 右 | 说明
--- | --- | --- | --- | ---
x | 010110 | 0 | 1 |
~x | 101001 | 1 | 0 |
x + 1 | 010110 | 1 | 0 | 加 1 时, 右侧的 1 进位全变为 0, 0 得到进位变为1

## 将最右侧的 0 置 1
```python
def set_rightmost_0bit(x):
    return x | x + 1
```
示例:
```
    01011011    (x)
|   01011100    (x+1)
    --------
    01011111

    00000000    (x)
|   00000001    (x+1)
    --------
    00000000
```

## 参考资料
- [Low Level Bit Hacks You Absolutely Must Know](http://www.catonmat.net/blog/low-level-bit-hacks-you-absolutely-must-know/)
