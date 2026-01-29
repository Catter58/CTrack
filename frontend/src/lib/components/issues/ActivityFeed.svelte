<script lang="ts">
	import type { Activity } from '$lib/stores/issue';

	interface Props {
		activities: Activity[];
	}

	let { activities }: Props = $props();

	const actionLabels: Record<string, string> = {
		created: 'создал(а) задачу',
		updated: 'обновил(а)',
		status_changed: 'изменил(а) статус',
		assigned: 'назначил(а) исполнителя',
		commented: 'добавил(а) комментарий',
		attachment_added: 'добавил(а) вложение'
	};

	function formatTimestamp(dateStr: string): string {
		return new Date(dateStr).toLocaleString('ru-RU', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getUserName(user: Activity['user']): string {
		if (!user) return 'Система';
		if (user.full_name?.trim()) return user.full_name;
		const fullName = [user.first_name, user.last_name].filter(Boolean).join(' ').trim();
		if (fullName) return fullName;
		return user.username;
	}

	function getUserInitials(user: Activity['user']): string {
		if (!user) return 'С';
		const name = getUserName(user);
		const parts = name.split(' ');
		if (parts.length >= 2) {
			return (parts[0][0] + parts[1][0]).toUpperCase();
		}
		return name.slice(0, 2).toUpperCase();
	}

	function getActionDescription(activity: Activity): string {
		if (activity.action === 'updated' && activity.field_name) {
			return `${actionLabels.updated} ${activity.field_name}`;
		}
		if (activity.action === 'status_changed') {
			const oldStatus = formatValue(activity.old_value);
			const newStatus = formatValue(activity.new_value);
			return `${actionLabels.status_changed} с ${oldStatus} на ${newStatus}`;
		}
		return actionLabels[activity.action] || activity.action;
	}

	function formatValue(value: Record<string, unknown> | null): string {
		if (value === null) return '—';
		if (typeof value === 'object' && 'name' in value) {
			return String(value.name);
		}
		if (typeof value === 'object' && 'value' in value) {
			return String(value.value);
		}
		return JSON.stringify(value);
	}

	function hasValueChange(activity: Activity): boolean {
		if (activity.action === 'status_changed' || activity.action === 'created') {
			return false;
		}
		return (
			activity.action === 'updated' &&
			activity.field_name !== '' &&
			(activity.old_value !== null || activity.new_value !== null)
		);
	}
</script>

<section class="activity-feed">
	<h3>История изменений ({activities.length})</h3>

	{#if activities.length > 0}
		<div class="timeline">
			{#each activities as activity (activity.id)}
				<div class="activity-item">
					<div class="avatar">
						{getUserInitials(activity.user)}
					</div>
					<div class="activity-content">
						<div class="activity-header">
							<span class="user-name">{getUserName(activity.user)}</span>
							<span class="action">{getActionDescription(activity)}</span>
						</div>
						{#if hasValueChange(activity)}
							<div class="value-change">
								<span class="old-value">{formatValue(activity.old_value)}</span>
								<span class="arrow">&rarr;</span>
								<span class="new-value">{formatValue(activity.new_value)}</span>
							</div>
						{/if}
						<span class="timestamp">{formatTimestamp(activity.created_at)}</span>
					</div>
				</div>
			{/each}
		</div>
	{:else}
		<p class="empty-message">История изменений пуста</p>
	{/if}
</section>

<style>
	.activity-feed {
		margin-top: 2rem;
		padding-top: 2rem;
		border-top: 1px solid var(--cds-border-subtle);
	}

	h3 {
		font-size: 1rem;
		font-weight: 600;
		margin: 0 0 1rem;
	}

	.timeline {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.activity-item {
		display: flex;
		gap: 0.75rem;
		padding: 0.75rem;
		background: var(--cds-field);
		border-radius: 4px;
	}

	.avatar {
		width: 2rem;
		height: 2rem;
		border-radius: 50%;
		background: var(--cds-interactive);
		color: var(--cds-text-on-color);
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 0.75rem;
		font-weight: 600;
		flex-shrink: 0;
	}

	.activity-content {
		flex: 1;
		min-width: 0;
	}

	.activity-header {
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem;
		margin-bottom: 0.25rem;
	}

	.user-name {
		font-weight: 500;
		color: var(--cds-text-primary);
	}

	.action {
		color: var(--cds-text-secondary);
	}

	.value-change {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin: 0.5rem 0;
		padding: 0.5rem;
		background: var(--cds-layer);
		border-radius: 4px;
		font-size: 0.875rem;
	}

	.old-value {
		color: var(--cds-text-secondary);
		text-decoration: line-through;
	}

	.arrow {
		color: var(--cds-text-secondary);
	}

	.new-value {
		color: var(--cds-text-primary);
		font-weight: 500;
	}

	.timestamp {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
	}

	.empty-message {
		color: var(--cds-text-secondary);
		font-style: italic;
		text-align: center;
		padding: 1rem;
	}
</style>
