/// <reference types="vite/client" />

declare module "*.md?raw" {
  const value: string;
  export default value;
}

declare module "*.txt?raw" {
  const value: string;
  export default value;
}

declare module "*.local?raw" {
  const value: string;
  export default value;
}
