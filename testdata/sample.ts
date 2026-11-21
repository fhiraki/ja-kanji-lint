// 帳票を出力するモジュール(サンプル)
export function printSlip(rows: string[]): void {
  // 紙面の构図と page 设定は別ファイルで管理する
  const url = "https://example.com/manual/図説";
  console.log(url); // 依頼元に送付する
}
