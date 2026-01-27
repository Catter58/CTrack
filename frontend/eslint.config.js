import js from "@eslint/js";
import ts from "typescript-eslint";
import svelte from "eslint-plugin-svelte";
import globals from "globals";

export default ts.config(
  js.configs.recommended,
  ...ts.configs.recommended,
  ...svelte.configs["flat/recommended"],
  {
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
  },
  {
    files: ["**/*.svelte"],
    languageOptions: {
      parserOptions: {
        parser: ts.parser,
      },
    },
  },
  {
    rules: {
      // Disable strict navigation rules - static routes don't need resolve()
      "svelte/no-navigation-without-resolve": "off",
      // Each blocks with simple iteration don't always need keys
      "svelte/require-each-key": "warn",
      // Allow @html for trusted content (EditorJS)
      "svelte/no-at-html-tags": "warn",
      // SvelteDate is not always needed for simple date handling
      "svelte/prefer-svelte-reactivity": "warn",
    },
  },
  {
    ignores: ["build/", ".svelte-kit/", "dist/"],
  },
);
