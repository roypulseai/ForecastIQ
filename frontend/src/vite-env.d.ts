/// <reference types="vite/client" />

declare module 'react-dropzone' {
  import { DropzoneOptions, DropzoneState } from 'react-dropzone'

  export interface UseDropzoneOptions extends DropzoneOptions {
    children?: (state: DropzoneState) => React.ReactNode
  }

  export function useDropzone(options?: UseDropzoneOptions): DropzoneState
}
