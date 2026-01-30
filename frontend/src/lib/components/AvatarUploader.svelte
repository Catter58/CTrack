<script lang="ts">
	import { Button, Modal, Loading, InlineNotification } from 'carbon-components-svelte';
	import { Upload, TrashCan, Crop, UserAvatar } from 'carbon-icons-svelte';
	import api, { resolveMediaUrl } from '$lib/api/client';

	interface Props {
		userId: number;
		currentAvatar?: string | null;
		onUpdate?: (avatarUrl: string | null) => void;
	}

	let { userId, currentAvatar = null, onUpdate }: Props = $props();

	// Resolve avatar URL to full URL
	const avatarUrl = $derived(resolveMediaUrl(currentAvatar));

	let fileInput: HTMLInputElement;
	let isUploading = $state(false);
	let isDeleting = $state(false);
	let error = $state<string | null>(null);

	// Cropper state
	let showCropper = $state(false);
	let selectedFile = $state<File | null>(null);
	let previewUrl = $state<string | null>(null);
	let imageRef = $state<HTMLImageElement | null>(null);
	let cropArea = $state({ x: 0, y: 0, size: 0 });
	let isDragging = $state(false);
	let dragStart = $state({ x: 0, y: 0 });
	let imageLoaded = $state(false);
	let displayScale = $state(1);

	function handleFileSelect(e: Event) {
		const target = e.target as HTMLInputElement;
		const file = target.files?.[0];
		if (!file) return;

		// Validate file type
		if (!['image/jpeg', 'image/png', 'image/gif', 'image/webp'].includes(file.type)) {
			error = 'Допустимые форматы: JPEG, PNG, GIF, WebP';
			return;
		}

		// Validate file size (5MB)
		if (file.size > 5 * 1024 * 1024) {
			error = 'Максимальный размер файла: 5 МБ';
			return;
		}

		error = null;
		selectedFile = file;
		previewUrl = URL.createObjectURL(file);
		imageLoaded = false;
		showCropper = true;
	}

	function handleImageLoad(e: Event) {
		const img = e.target as HTMLImageElement;
		imageRef = img;

		// Calculate initial crop area (centered square)
		const minDim = Math.min(img.naturalWidth, img.naturalHeight);
		cropArea = {
			x: (img.naturalWidth - minDim) / 2,
			y: (img.naturalHeight - minDim) / 2,
			size: minDim
		};

		// Calculate display scale to fit in container
		const containerSize = 400;
		displayScale = Math.min(containerSize / img.naturalWidth, containerSize / img.naturalHeight, 1);

		imageLoaded = true;
	}

	function handleMouseDown(e: MouseEvent) {
		if (!imageLoaded) return;
		isDragging = true;
		dragStart = { x: e.clientX, y: e.clientY };
	}

	function handleMouseMove(e: MouseEvent) {
		if (!isDragging || !imageRef) return;

		const dx = (e.clientX - dragStart.x) / displayScale;
		const dy = (e.clientY - dragStart.y) / displayScale;

		const maxX = imageRef.naturalWidth - cropArea.size;
		const maxY = imageRef.naturalHeight - cropArea.size;

		cropArea = {
			...cropArea,
			x: Math.max(0, Math.min(maxX, cropArea.x + dx)),
			y: Math.max(0, Math.min(maxY, cropArea.y + dy))
		};

		dragStart = { x: e.clientX, y: e.clientY };
	}

	function handleMouseUp() {
		isDragging = false;
	}

	function handleWheel(e: WheelEvent) {
		if (!imageLoaded || !imageRef) return;
		e.preventDefault();

		const delta = e.deltaY > 0 ? -20 : 20;
		const minSize = 50;
		const maxSize = Math.min(imageRef.naturalWidth, imageRef.naturalHeight);

		const newSize = Math.max(minSize, Math.min(maxSize, cropArea.size + delta));

		// Adjust position to keep crop centered
		const sizeDiff = newSize - cropArea.size;
		const newX = Math.max(0, Math.min(imageRef.naturalWidth - newSize, cropArea.x - sizeDiff / 2));
		const newY = Math.max(0, Math.min(imageRef.naturalHeight - newSize, cropArea.y - sizeDiff / 2));

		cropArea = { x: newX, y: newY, size: newSize };
	}

	async function handleUpload() {
		if (!selectedFile || !imageRef) return;

		isUploading = true;
		error = null;

		try {
			// Create cropped image on canvas
			const canvas = document.createElement('canvas');
			const ctx = canvas.getContext('2d')!;
			const outputSize = 256;

			canvas.width = outputSize;
			canvas.height = outputSize;

			// Draw cropped area
			ctx.drawImage(
				imageRef,
				cropArea.x,
				cropArea.y,
				cropArea.size,
				cropArea.size,
				0,
				0,
				outputSize,
				outputSize
			);

			// Convert to blob
			const blob = await new Promise<Blob>((resolve) => {
				canvas.toBlob((b) => resolve(b!), 'image/jpeg', 0.9);
			});

			// Create FormData
			const formData = new FormData();
			formData.append('file', blob, 'avatar.jpg');

			// Upload
			const response = await api.upload<{ avatar_url: string }>(
				`/api/users/${userId}/avatar`,
				formData
			);

			onUpdate?.(response.avatar_url);
			closeCropper();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Не удалось загрузить аватар';
		} finally {
			isUploading = false;
		}
	}

	async function handleDelete() {
		isDeleting = true;
		error = null;

		try {
			await api.delete(`/api/users/${userId}/avatar`);
			onUpdate?.(null);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Не удалось удалить аватар';
		} finally {
			isDeleting = false;
		}
	}

	function closeCropper() {
		showCropper = false;
		if (previewUrl) {
			URL.revokeObjectURL(previewUrl);
			previewUrl = null;
		}
		selectedFile = null;
		imageLoaded = false;
		if (fileInput) fileInput.value = '';
	}

	function openFilePicker() {
		fileInput?.click();
	}
</script>

<div class="avatar-uploader">
	<div class="avatar-preview">
		{#if avatarUrl}
			<img src={avatarUrl} alt="Аватар" class="avatar-image" />
		{:else}
			<div class="avatar-placeholder">
				<UserAvatar size={32} />
			</div>
		{/if}
	</div>

	<div class="avatar-actions">
		<input
			bind:this={fileInput}
			type="file"
			accept="image/jpeg,image/png,image/gif,image/webp"
			onchange={handleFileSelect}
			hidden
		/>
		<Button kind="secondary" icon={Upload} size="small" on:click={openFilePicker}>
			{currentAvatar ? 'Изменить' : 'Загрузить'}
		</Button>
		{#if currentAvatar}
			<Button
				kind="danger-ghost"
				icon={TrashCan}
				size="small"
				disabled={isDeleting}
				on:click={handleDelete}
			>
				{isDeleting ? 'Удаление...' : 'Удалить'}
			</Button>
		{/if}
	</div>

	{#if error}
		<InlineNotification
			kind="error"
			title="Ошибка"
			subtitle={error}
			lowContrast
			on:close={() => (error = null)}
		/>
	{/if}
</div>

<Modal
	bind:open={showCropper}
	modalHeading="Обрезка изображения"
	primaryButtonText={isUploading ? 'Загрузка...' : 'Сохранить'}
	secondaryButtonText="Отмена"
	primaryButtonDisabled={!imageLoaded || isUploading}
	primaryButtonIcon={isUploading ? undefined : Crop}
	on:click:button--primary={handleUpload}
	on:click:button--secondary={closeCropper}
	on:close={closeCropper}
>
	<div class="cropper-container">
		{#if !imageLoaded}
			<div class="cropper-loading">
				<Loading withOverlay={false} small />
			</div>
		{/if}

		{#if previewUrl}
			<div
				class="cropper-wrapper"
				class:loaded={imageLoaded}
				style="width: {imageRef ? imageRef.naturalWidth * displayScale : 400}px; height: {imageRef
					? imageRef.naturalHeight * displayScale
					: 400}px;"
				onmousedown={handleMouseDown}
				onmousemove={handleMouseMove}
				onmouseup={handleMouseUp}
				onmouseleave={handleMouseUp}
				onwheel={handleWheel}
				role="application"
				aria-label="Область обрезки"
			>
				<img
					src={previewUrl}
					alt="Предпросмотр"
					class="cropper-image"
					onload={handleImageLoad}
					style="transform: scale({displayScale}); transform-origin: top left;"
				/>

				{#if imageLoaded}
					<!-- Dark overlay -->
					<div class="cropper-overlay"></div>

					<!-- Crop area (visible part) -->
					<div
						class="crop-area"
						style="
							left: {cropArea.x * displayScale}px;
							top: {cropArea.y * displayScale}px;
							width: {cropArea.size * displayScale}px;
							height: {cropArea.size * displayScale}px;
						"
					>
						<img
							src={previewUrl}
							alt=""
							class="crop-preview"
							style="
								transform: scale({displayScale});
								transform-origin: top left;
								margin-left: -{cropArea.x * displayScale}px;
								margin-top: -{cropArea.y * displayScale}px;
							"
						/>
					</div>
				{/if}
			</div>
		{/if}

		<p class="cropper-hint">
			Перетащите область выделения или используйте колёсико мыши для изменения размера
		</p>
	</div>
</Modal>

<style>
	.avatar-uploader {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.avatar-preview {
		width: 120px;
		height: 120px;
		border-radius: 50%;
		overflow: hidden;
		background: var(--cds-layer);
		border: 2px solid var(--cds-border-subtle);
	}

	.avatar-image {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.avatar-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--cds-text-secondary);
	}

	.avatar-actions {
		display: flex;
		gap: 0.5rem;
		flex-wrap: wrap;
	}

	.cropper-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
		min-height: 300px;
	}

	.cropper-loading {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 300px;
	}

	.cropper-wrapper {
		position: relative;
		overflow: hidden;
		cursor: move;
		max-width: 100%;
		max-height: 400px;
		background: var(--cds-layer);
		opacity: 0;
		transition: opacity 0.2s;
	}

	.cropper-wrapper.loaded {
		opacity: 1;
	}

	.cropper-image {
		display: block;
		max-width: none;
	}

	.cropper-overlay {
		position: absolute;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		pointer-events: none;
	}

	.crop-area {
		position: absolute;
		overflow: hidden;
		border: 2px solid var(--cds-interactive);
		border-radius: 50%;
		pointer-events: none;
		box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.6);
	}

	.crop-preview {
		display: block;
		max-width: none;
	}

	.cropper-hint {
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
		text-align: center;
		margin: 0;
	}

	:global(.avatar-uploader .bx--inline-notification) {
		max-width: 100%;
		margin-top: 0.5rem;
	}
</style>
