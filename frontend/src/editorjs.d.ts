// Type declarations for EditorJS plugins
// These packages don't have @types packages available

declare module "@editorjs/header" {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const Header: any;
  export default Header;
}

declare module "@editorjs/list" {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const List: any;
  export default List;
}

declare module "@editorjs/quote" {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const Quote: any;
  export default Quote;
}

declare module "@editorjs/code" {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const CodeTool: any;
  export default CodeTool;
}

declare module "@editorjs/marker" {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const Marker: any;
  export default Marker;
}
