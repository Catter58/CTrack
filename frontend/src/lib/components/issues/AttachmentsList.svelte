<script lang="ts">
	import { Button, InlineLoading } from 'carbon-components-svelte';
	import { Download, TrashCan, Document, Image, Archive, DocumentPdf } from 'carbon-icons-svelte';
	import type { Attachment } from '$lib/stores/issue';
	import api from '$lib/api/client';

	interface Props {
		attachments: Attachment[];
		onDelete: (id: string) => void;
		canDelete?: (attachment: Attachment) => boolean;
	}

	let { attachments, onDelete, canDelete = () => true }: Props = $props();

	let deletingId = $state<string | null>(null);
	let downloadingId = $state<string | null>(null);
	// eslint-disable-next-line @typescript-eslint/no-unused-vars
	let downloadError = $state<string | null>(null);

	function formatFileSize(bytes: number): string {
		if (bytes === 0) return '0 Б';
		const units = ['Б', 'КБ', 'МБ', 'ГБ'];
		const i = Math.floor(Math.log(bytes) / Math.log(1024));
		const size = bytes / Math.pow(1024, i);
		return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleString('ru-RU', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatUserName(user: {
		first_name?: string | null;
		last_name?: string | null;
		full_name?: string | null;
		username: string;
	}): string {
		if (user.full_name?.trim()) return user.full_name;
		const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ').trim();
		if (fullName) return fullName;
		return user.username;
	}

	function getFileIcon(contentType: string) {
		if (contentType.startsWith('image/')) return Image;
		if (contentType === 'application/pdf') return DocumentPdf;
		if (
			contentType.includes('zip') ||
			contentType.includes('tar') ||
			contentType.includes('rar') ||
			contentType.includes('7z')
		) {
			return Archive;
		}
		return Document;
	}

	async function handleDownload(attachment: Attachment) {
		downloadingId = attachment.id;
		downloadError = null;
		try {
			await api.downloadFile(`/api/attachments/${attachment.id}/download`, attachment.filename);
		} catch (err) {
			downloadError = err instanceof Error ? err.message : 'Ошибка скачивания файла';
		} finally {
			downloadingId = null;
		}
	}

	async function handleDelete(attachment: Attachment) {
		deletingId = attachment.id;
		try {
			await onDelete(attachment.id);
		} finally {
			deletingId = null;
		}
	}
</script>

{#if attachments.length === 0}
	<p class="empty-message">Нет вложений</p>
{:else}
	<div class="attachments-list">
		{#each attachments as attachment (attachment.id)}
			{@const FileIcon = getFileIcon(attachment.content_type)}
			<div class="attachment-item">
				<div class="attachment-icon">
					<FileIcon size={24} />
				</div>
				<div class="attachment-info">
					<span class="attachment-name">{attachment.filename}</span>
					<span class="attachment-meta">
						{formatFileSize(attachment.file_size)} | {formatUserName(attachment.uploaded_by)} |
						{formatDate(attachment.created_at)}
					</span>
				</div>
				<div class="attachment-actions">
					{#if downloadingId === attachment.id}
						<InlineLoading description="" />
					{:else}
						<Button
							kind="ghost"
							size="small"
							icon={Download}
							iconDescription="Скачать"
							on:click={() => handleDownload(attachment)}
						/>
					{/if}
					{#if canDelete(attachment)}
						{#if deletingId === attachment.id}
							<InlineLoading description="" />
						{:else}
							<Button
								kind="danger-ghost"
								size="small"
								icon={TrashCan}
								iconDescription="Удалить"
								on:click={() => handleDelete(attachment)}
							/>
						{/if}
					{/if}
				</div>
			</div>
		{/each}
	</div>
{/if}

<style>
	.attachments-list {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.attachment-item {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.75rem;
		background: var(--cds-layer);
		border-radius: 4px;
		border: 1px solid var(--cds-border-subtle);
	}

	.attachment-icon {
		color: var(--cds-icon-secondary);
		flex-shrink: 0;
	}

	.attachment-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.attachment-name {
		font-size: 0.875rem;
		font-weight: 500;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.attachment-meta {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}

	.attachment-actions {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		flex-shrink: 0;
	}

	.empty-message {
		color: var(--cds-text-secondary);
		font-size: 0.875rem;
		text-align: center;
		padding: 1rem;
	}
</style>
