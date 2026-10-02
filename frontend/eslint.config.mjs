import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  { rules: { "@next/next/no-img-element": "off" } }, // 私有图片通过带鉴权的 Blob URL 展示，无法交给 Next 图片优化器读取。
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);
