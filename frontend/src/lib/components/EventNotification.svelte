<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { toasts } from '$lib/stores/toast';
	import { events, type SSEEvent, type IssueEventData, type CommentEventData } from '$lib/stores/events';
	import { user } from '$lib/stores/auth';

	// Rate limiting for notifications
	const NOTIFICATION_COOLDOWN = 2000; // 2 seconds between notifications of same type
	const MAX_NOTIFICATIONS_PER_MINUTE = 10;

	let notificationCounts = $state<Map<string, number>>(new Map());
	let lastNotificationTime = $state<Map<string, number>>(new Map());
	let minuteNotificationCount = $state(0);
	let minuteResetTimeout: ReturnType<typeof setTimeout> | null = null;

	let unsubscribers: (() => void)[] = [];

	function resetMinuteCount(): void {
		minuteNotificationCount = 0;
		minuteResetTimeout = setTimeout(resetMinuteCount, 60000);
	}

	function canShowNotification(eventType: string): boolean {
		// Check global rate limit
		if (minuteNotificationCount >= MAX_NOTIFICATIONS_PER_MINUTE) {
			return false;
		}

		// Check per-type cooldown
		const lastTime = lastNotificationTime.get(eventType) || 0;
		if (Date.now() - lastTime < NOTIFICATION_COOLDOWN) {
			return false;
		}

		return true;
	}

	function recordNotification(eventType: string): void {
		minuteNotificationCount++;
		lastNotificationTime.set(eventType, Date.now());
		notificationCounts.set(eventType, (notificationCounts.get(eventType) || 0) + 1);
	}

	function isOwnAction(eventUser: { id: number; username: string } | undefined): boolean {
		const currentUser = $user;
		if (!currentUser || !eventUser) return false;
		return currentUser.id === eventUser.id;
	}

	function handleIssueCreated(event: SSEEvent): void {
		const data = event.data as unknown as IssueEventData;
		if (!data || isOwnAction(data.user)) return;

		if (!canShowNotification('issue.created')) return;
		recordNotification('issue.created');

		const issueKey = data.issue_key || `#${data.issue_id}`;
		toasts.info(
			`Создана задача ${issueKey}`,
			data.user ? `Автор: ${data.user.username}` : undefined,
			5000
		);
	}

	function handleIssueUpdated(event: SSEEvent): void {
		const data = event.data as unknown as IssueEventData;
		if (!data || isOwnAction(data.user)) return;

		if (!canShowNotification('issue.updated')) return;
		recordNotification('issue.updated');

		const issueKey = data.issue_key || `#${data.issue_id}`;
		const changes = data.changes ? Object.keys(data.changes).join(', ') : '';
		const subtitle = data.user
			? `${data.user.username}${changes ? `: ${changes}` : ''}`
			: changes || undefined;

		toasts.info(`Обновлена задача ${issueKey}`, subtitle, 5000);
	}

	function handleIssueMoved(event: SSEEvent): void {
		const data = event.data as unknown as IssueEventData;
		if (!data || isOwnAction(data.user)) return;

		if (!canShowNotification('issue.moved')) return;
		recordNotification('issue.moved');

		const issueKey = data.issue_key || `#${data.issue_id}`;
		toasts.info(
			`Задача ${issueKey} перемещена`,
			data.user ? `Пользователем: ${data.user.username}` : undefined,
			5000
		);
	}

	function handleIssueDeleted(event: SSEEvent): void {
		const data = event.data as unknown as IssueEventData;
		if (!data || isOwnAction(data.user)) return;

		if (!canShowNotification('issue.deleted')) return;
		recordNotification('issue.deleted');

		const issueKey = data.issue_key || `#${data.issue_id}`;
		toasts.warning(
			`Удалена задача ${issueKey}`,
			data.user ? `Пользователем: ${data.user.username}` : undefined,
			5000
		);
	}

	function handleCommentCreated(event: SSEEvent): void {
		const data = event.data as unknown as CommentEventData;
		if (!data || isOwnAction(data.user)) return;

		if (!canShowNotification('comment.created')) return;
		recordNotification('comment.created');

		const issueKey = data.issue_key;
		toasts.info(
			`Новый комментарий к ${issueKey}`,
			data.user ? `От: ${data.user.username}` : undefined,
			5000
		);
	}

	function handleConnectionEvent(event: SSEEvent): void {
		if (event.type === 'connected') {
			console.log('[EventNotification] Connected to SSE, channels:', event.channels);
		} else if (event.type === 'error') {
			console.error('[EventNotification] SSE error:', event.message);
		}
	}

	onMount(() => {
		// Start minute counter reset
		resetMinuteCount();

		// Subscribe to events
		unsubscribers = [
			events.on('issue.created', handleIssueCreated),
			events.on('issue.updated', handleIssueUpdated),
			events.on('issue.moved', handleIssueMoved),
			events.on('issue.deleted', handleIssueDeleted),
			events.on('comment.created', handleCommentCreated),
			events.on('comment.added', handleCommentCreated), // Alternative event name
			events.on('connected', handleConnectionEvent),
			events.on('error', handleConnectionEvent),
		];
	});

	onDestroy(() => {
		// Cleanup subscriptions
		unsubscribers.forEach((unsub) => unsub());

		if (minuteResetTimeout) {
			clearTimeout(minuteResetTimeout);
		}
	});
</script>
