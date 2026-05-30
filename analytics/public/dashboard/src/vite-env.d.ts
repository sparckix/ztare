/// <reference types="vite/client" />

declare module "*.md?raw" {
  const content: string;
  export default content;
}

declare module "*.json" {
  const value: any;
  export default value;
}
