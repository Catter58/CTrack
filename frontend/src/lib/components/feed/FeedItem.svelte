<script lang="ts">
	import {
		Add,
		ArrowRight,
		User,
		UserFollow,
		Flag,
		Calendar,
		Star,
		Attachment,
		TrashCan,
		Chat,
		Image,
		DocumentPdf,
		DocumentBlank,
		Archive,
		Code,
		VideoChat
	} from 'carbon-icons-svelte';
	import { Link } from 'carbon-components-svelte';
	import type { FeedItem, FeedAction } from '$lib/stores/feed';
	import { actionLabels } from '$lib/stores/feed';
	import { resolveMediaUrl } from '$lib/api/client';

	interface Props {
		item: FeedItem;
	}

	let { item }: Props = $props();

	// Icons and colors for each action type
	const actionConfig: Record<FeedAction, { icon: typeof Add; color: string }> = {
		created: { icon: Add, color: '#24a148' },
		status_changed: { icon: ArrowRight, color: '#0f62fe' },
		assigned: { icon: User, color: '#8a3ffc' },
		unassigned: { icon: UserFollow, color: '#6f6f6f' },
		priority_changed: { icon: Flag, color: '#ff832b' },
		due_date_changed: { icon: Calendar, color: '#6f6f6f' },
		story_points_changed: { icon: Star, color: '#f1c21b' },
		attachment_added: { icon: Attachment, color: '#1192e8' },
		attachment_removed: { icon: TrashCan, color: '#da1e28' },
		commented: { icon: Chat, color: '#0f62fe' }
	};

	// Priority labels for display
	const priorityLabels: Record<string, string> = {
		highest: 'Критический',
		high: 'Высокий',
		medium: 'Средний',
		low: 'Низкий',
		lowest: 'Минимальный'
	};

	let config = $derived(actionConfig[item.action] || actionConfig.created);

	function getUserName(user: FeedItem['user']): string {
		if (!user) return 'Система';
		return user.full_name?.trim() || user.username;
	}

	function getUserInitials(user: FeedItem['user']): string {
		if (!user) return 'С';
		const name = getUserName(user);
		const parts = name.split(' ');
		if (parts.length >= 2) {
			return (parts[0][0] + parts[1][0]).toUpperCase();
		}
		return name.slice(0, 2).toUpperCase();
	}

	function formatRelativeTime(dateStr: string): string {
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / (1000 * 60));
		const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

		if (diffMins < 1) return 'только что';
		if (diffMins < 60) return `${diffMins} мин. назад`;
		if (diffHours < 24) return `${diffHours} ч. назад`;
		if (diffDays === 1) return 'вчера';
		if (diffDays < 7) return `${diffDays} дн. назад`;

		return date.toLocaleDateString('ru-RU', {
			day: 'numeric',
			month: 'short'
		});
	}

	function formatValue(value: unknown, type: 'status' | 'priority' | 'date' | 'sp' | 'user' | 'generic'): string {
		if (value === null || value === undefined) return '-';

		if (type === 'status') {
			if (typeof value === 'object' && value !== null && 'name' in value) {
				return String((value as { name: string }).name);
			}
			return String(value);
		}

		if (type === 'priority') {
			const strVal = typeof value === 'object' && value !== null && 'value' in value
				? String((value as { value: string }).value)
				: String(value);
			return priorityLabels[strVal] || strVal;
		}

		if (type === 'date') {
			const dateVal = typeof value === 'object' && value !== null && 'value' in value
				? String((value as { value: string }).value)
				: String(value);
			try {
				return new Date(dateVal).toLocaleDateString('ru-RU', {
					day: 'numeric',
					month: 'short',
					year: 'numeric'
				});
			} catch {
				return dateVal;
			}
		}

		if (type === 'sp') {
			if (typeof value === 'object' && value !== null && 'value' in value) {
				return String((value as { value: number }).value);
			}
			return String(value);
		}

		if (type === 'user') {
			if (typeof value === 'object' && value !== null) {
				const userObj = value as { full_name?: string; username?: string; name?: string };
				return userObj.full_name || userObj.username || userObj.name || '-';
			}
			return String(value);
		}

		return String(value);
	}

	function getValueType(action: FeedAction): 'status' | 'priority' | 'date' | 'sp' | 'user' | 'generic' {
		switch (action) {
			case 'status_changed':
				return 'status';
			case 'priority_changed':
				return 'priority';
			case 'due_date_changed':
				return 'date';
			case 'story_points_changed':
				return 'sp';
			case 'assigned':
			case 'unassigned':
				return 'user';
			default:
				return 'generic';
		}
	}

	let hasValueChange = $derived(
		item.action === 'status_changed' ||
			item.action === 'priority_changed' ||
			item.action === 'story_points_changed'
	);

	let valueType = $derived(getValueType(item.action));

	// Get attachment filename from activity data
	function getAttachmentFilename(): string | null {
		if (item.action === 'attachment_added' && item.new_value) {
			const val = item.new_value as { filename?: string };
			return val.filename || null;
		}
		if (item.action === 'attachment_removed' && item.old_value) {
			const val = item.old_value as { filename?: string };
			return val.filename || null;
		}
		return null;
	}

	// Get file icon based on extension
	function getFileIconType(filename: string): 'image' | 'pdf' | 'archive' | 'code' | 'video' | 'document' {
		const ext = filename.split('.').pop()?.toLowerCase() || '';

		const imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico'];
		const pdfExtensions = ['pdf'];
		const archiveExtensions = ['zip', 'rar', '7z', 'tar', 'gz', 'bz2'];
		const codeExtensions = ['js', 'ts', 'py', 'java', 'c', 'cpp', 'h', 'go', 'rs', 'rb', 'php', 'html', 'css', 'scss', 'json', 'xml', 'yaml', 'yml', 'md', 'svelte', 'vue', 'jsx', 'tsx'];
		const videoExtensions = ['mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv'];

		if (imageExtensions.includes(ext)) return 'image';
		if (pdfExtensions.includes(ext)) return 'pdf';
		if (archiveExtensions.includes(ext)) return 'archive';
		if (codeExtensions.includes(ext)) return 'code';
		if (videoExtensions.includes(ext)) return 'video';
		return 'document';
	}

	let attachmentFilename = $derived(getAttachmentFilename());
	let fileIconType = $derived(attachmentFilename ? getFileIconType(attachmentFilename) : null);
</script>

<div class="feed-item">
	<div class="item-icon" style="background-color: {config.color}">
		{#if item.action === 'created'}
			<Add size={16} />
		{:else if item.action === 'status_changed'}
			<ArrowRight size={16} />
		{:else if item.action === 'assigned'}
			<User size={16} />
		{:else if item.action === 'unassigned'}
			<UserFollow size={16} />
		{:else if item.action === 'priority_changed'}
			<Flag size={16} />
		{:else if item.action === 'due_date_changed'}
			<Calendar size={16} />
		{:else if item.action === 'story_points_changed'}
			<Star size={16} />
		{:else if item.action === 'attachment_added'}
			<Attachment size={16} />
		{:else if item.action === 'attachment_removed'}
			<TrashCan size={16} />
		{:else if item.action === 'commented'}
			<Chat size={16} />
		{:else}
			<Add size={16} />
		{/if}
	</div>

	<div class="item-content">
		<div class="item-header">
			<div class="avatar">
				{#if item.user.avatar}
					<img src={resolveMediaUrl(item.user.avatar)} alt={getUserName(item.user)} />
				{:else}
					{getUserInitials(item.user)}
				{/if}
			</div>
			<div class="header-text">
				<span class="user-name">{getUserName(item.user)}</span>
				<span class="action">{actionLabels[item.action]}</span>
			</div>
		</div>

		<div class="issue-info">
			<Link href="/issues/{item.issue.key}" class="issue-link">
				{item.issue.key}
			</Link>
			<span class="issue-title">{item.issue.title}</span>
		</div>

		<div class="project-name">
			{item.issue.project.name}
		</div>

		{#if hasValueChange}
			<div class="value-change">
				<span class="old-value">{formatValue(item.old_value, valueType)}</span>
				<ArrowRight size={16} />
				<span class="new-value">{formatValue(item.new_value, valueType)}</span>
			</div>
		{/if}

		{#if item.action === 'commented' && item.comment_preview}
			<div class="comment-preview">
				"{item.comment_preview}"
			</div>
		{/if}

		{#if item.action === 'assigned' && item.new_value}
			<div class="assigned-user">
				{formatValue(item.new_value, 'user')}
			</div>
		{/if}

		{#if (item.action === 'attachment_added' || item.action === 'attachment_removed') && attachmentFilename}
			<div class="attachment-info" class:removed={item.action === 'attachment_removed'}>
				<span class="file-icon">
					{#if fileIconType === 'image'}
						<Image size={16} />
					{:else if fileIconType === 'pdf'}
						<DocumentPdf size={16} />
					{:else if fileIconType === 'archive'}
						<Archive size={16} />
					{:else if fileIconType === 'code'}
						<Code size={16} />
					{:else if fileIconType === 'video'}
						<VideoChat size={16} />
					{:else}
						<DocumentBlank size={16} />
					{/if}
				</span>
				<span class="filename">{attachmentFilename}</span>
			</div>
		{/if}

		<span class="timestamp">{formatRelativeTime(item.created_at)}</span>
	</div>
</div>

<style>
	.feed-item {
		display: flex;
		gap: 0.75rem;
		padding: 1rem;
		background: var(--cds-field);
		border-radius: 6px;
		position: relative;
	}

	.item-icon {
		width: 2rem;
		height: 2rem;
		border-radius: 50%;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		color: white;
	}

	.item-content {
		flex: 1;
		min-width: 0;
	}

	.item-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.avatar {
		width: 1.5rem;
		height: 1.5rem;
		border-radius: 50%;
		background: var(--cds-interactive);
		color: var(--cds-text-on-color);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.625rem;
		font-weight: 600;
		flex-shrink: 0;
		overflow: hidden;
	}

	.avatar img {
		width: 100%;
		height: 100%;
		object-fit: cover;
	}

	.header-text {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem;
	}

	.user-name {
		font-weight: 500;
		color: var(--cds-text-primary);
	}

	.action {
		color: var(--cds-text-secondary);
	}

	.issue-info {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.25rem;
	}

	:global(.issue-info .bx--link) {
		font-weight: 500;
	}

	.issue-title {
		color: var(--cds-text-primary);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.project-name {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
		margin-bottom: 0.5rem;
	}

	.value-change {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem;
		background: var(--cds-layer);
		border-radius: 4px;
		font-size: 0.875rem;
		margin-bottom: 0.5rem;
	}

	.old-value {
		color: var(--cds-text-secondary);
		text-decoration: line-through;
	}

	.new-value {
		color: var(--cds-text-primary);
		font-weight: 500;
	}

	.comment-preview {
		padding: 0.5rem;
		background: var(--cds-layer);
		border-radius: 4px;
		border-left: 3px solid var(--cds-border-interactive);
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
		font-style: italic;
		margin-bottom: 0.5rem;
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.assigned-user {
		padding: 0.25rem 0.5rem;
		background: var(--cds-layer);
		border-radius: 4px;
		font-size: 0.875rem;
		color: var(--cds-text-primary);
		display: inline-block;
		margin-bottom: 0.5rem;
	}

	.attachment-info {
		display: inline-flex;
		align-items: center;
		gap: 0.375rem;
		padding: 0.375rem 0.625rem;
		background: var(--cds-layer);
		border-radius: 4px;
		font-size: 0.875rem;
		margin-bottom: 0.5rem;
		border-left: 3px solid #1192e8;
	}

	.attachment-info.removed {
		border-left-color: #da1e28;
	}

	.attachment-info.removed .filename {
		text-decoration: line-through;
		color: var(--cds-text-secondary);
	}

	.file-icon {
		display: flex;
		align-items: center;
		color: var(--cds-icon-secondary);
	}

	.filename {
		color: var(--cds-text-primary);
		word-break: break-all;
	}

	.timestamp {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}
</style>
