<script lang="ts">
	import { FileUploaderDropContainer, FileUploaderItem } from 'carbon-components-svelte';
	import type { Attachment } from '$lib/stores/issue';

	interface Props {
		onUpload: (file: File) => Promise<Attachment | null>;
	}

	let { onUpload }: Props = $props();

	interface UploadingFile {
		id: string;
		name: string;
		status: 'uploading' | 'complete' | 'edit';
		hasError: boolean;
		errorMessage?: string;
	}

	let uploadingFiles = $state<UploadingFile[]>([]);

	const acceptedTypes = [
		'image/*',
		'application/pdf',
		'.doc',
		'.docx',
		'.xls',
		'.xlsx',
		'.txt',
		'.csv',
		'.zip',
		'.rar',
		'.7z',
		'.tar',
		'.gz'
	];

	async function handleFilesAdded(event: CustomEvent<readonly File[]>) {
		const files = event.detail;

		for (const file of files) {
			const uploadId = crypto.randomUUID();
			uploadingFiles = [
				...uploadingFiles,
				{ id: uploadId, name: file.name, status: 'uploading', hasError: false }
			];

			try {
				const result = await onUpload(file);
				if (result) {
					uploadingFiles = uploadingFiles.map((f) =>
						f.id === uploadId ? { ...f, status: 'complete' as const, hasError: false } : f
					);
					setTimeout(() => {
						uploadingFiles = uploadingFiles.filter((f) => f.id !== uploadId);
					}, 2000);
				} else {
					uploadingFiles = uploadingFiles.map((f) =>
						f.id === uploadId
							? { ...f, status: 'edit' as const, hasError: true, errorMessage: 'Ошибка загрузки' }
							: f
					);
				}
			} catch (err) {
				const errorMessage = err instanceof Error ? err.message : 'Ошибка загрузки';
				uploadingFiles = uploadingFiles.map((f) =>
					f.id === uploadId
						? { ...f, status: 'edit' as const, hasError: true, errorMessage }
						: f
				);
			}
		}
	}

	function handleDeleteItem(event: CustomEvent<string>) {
		uploadingFiles = uploadingFiles.filter((f) => f.id !== event.detail);
	}
</script>

<div class="uploader-container">
	<FileUploaderDropContainer
		labelText="Перетащите файл сюда или нажмите для выбора"
		accept={acceptedTypes}
		multiple
		on:add={handleFilesAdded}
	/>

	{#if uploadingFiles.length > 0}
		<div class="uploading-files">
			{#each uploadingFiles as file (file.id)}
				<FileUploaderItem
					name={file.name}
					status={file.status}
					invalid={file.hasError}
					errorSubject={file.hasError ? 'Ошибка' : ''}
					errorBody={file.errorMessage ?? ''}
					on:delete={handleDeleteItem}
				/>
			{/each}
		</div>
	{/if}
</div>

<style>
	.uploader-container {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.uploading-files {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}
</style>
