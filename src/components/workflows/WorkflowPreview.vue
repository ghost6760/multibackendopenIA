<template>
  <div class="workflow-preview">
    <div class="preview-header">
      <h4>{{ workflow.name || 'Workflow sin nombre' }}</h4>
      <span v-if="workflow.enabled !== undefined" class="status-badge" :class="{ 'enabled': workflow.enabled }">
        {{ workflow.enabled ? '✅ Activo' : '⏸️ Inactivo' }}
      </span>
    </div>
    
    <p v-if="workflow.description" class="preview-description">
      {{ workflow.description }}
    </p>
    
    <div class="preview-stats">
      <div class="stat-item">
        <span class="stat-icon">🔢</span>
        <span class="stat-label">Nodos:</span>
        <span class="stat-value">{{ nodeCount }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-icon">🔗</span>
        <span class="stat-label">Conexiones:</span>
        <span class="stat-value">{{ edgeCount }}</span>
      </div>
    </div>
    
    <div v-if="workflow.nodes && workflow.nodes.length > 0" class="preview-nodes">
      <div class="nodes-header">📋 Flujo:</div>
      <div class="nodes-list">
        <div v-for="(node, index) in visibleNodes" :key="node.id" class="node-item">
          <span class="node-index">{{ index + 1 }}.</span>
          <span class="node-icon">{{ getNodeIcon(node.type) }}</span>
          <span class="node-name">{{ node.name || node.type }}</span>
        </div>
        <div v-if="workflow.nodes.length > maxVisibleNodes" class="nodes-more">
          +{{ workflow.nodes.length - maxVisibleNodes }} más...
        </div>
      </div>
    </div>
    
    <div v-if="workflow.tags && workflow.tags.length > 0" class="preview-tags">
      <span v-for="tag in workflow.tags" :key="tag" class="tag">
        #{{ tag }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  workflow: {
    type: Object,
    required: true
  },
  maxVisibleNodes: {
    type: Number,
    default: 5
  }
})

const nodeCount = computed(() => {
  if (Array.isArray(props.workflow.nodes)) {
    return props.workflow.nodes.length
  }
  if (typeof props.workflow.nodes === 'object') {
    return Object.keys(props.workflow.nodes).length
  }
  return 0
})

const edgeCount = computed(() => {
  if (Array.isArray(props.workflow.edges)) {
    return props.workflow.edges.length
  }
  if (typeof props.workflow.edges === 'object') {
    return Object.keys(props.workflow.edges).length
  }
  return 0
})

const visibleNodes = computed(() => {
  const nodes = Array.isArray(props.workflow.nodes) 
    ? props.workflow.nodes 
    : Object.values(props.workflow.nodes || {})
  
  return nodes.slice(0, props.maxVisibleNodes)
})

const getNodeIcon = (type) => {
  const icons = {
    'trigger': '🎯',
    'agent': '🤖',
    'tool': '🔧',
    'condition': '❓',
    'end': '🏁'
  }
  
  return icons[type?.toLowerCase()] || '📌'
}
</script>

<style scoped>
.workflow-preview {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 15px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.preview-header h4 {
  margin: 0;
  color: var(--text-primary);
  font-size: 1em;
}

.status-badge {
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 0.8em;
  background: var(--bg-secondary);
  color: var(--text-muted);
}

.status-badge.enabled {
  background: rgba(34, 197, 94, 0.1);
  color: var(--success-color);
}

.preview-description {
  margin: 0 0 12px 0;
  color: var(--text-secondary);
  font-size: 0.9em;
  line-height: 1.4;
}

.preview-stats {
  display: flex;
  gap: 15px;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.85em;
}

.stat-icon {
  font-size: 1em;
}

.stat-label {
  color: var(--text-muted);
}

.stat-value {
  color: var(--text-primary);
  font-weight: 600;
}

.preview-nodes {
  margin-bottom: 12px;
}

.nodes-header {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
  font-size: 0.9em;
}

.nodes-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.node-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: var(--bg-secondary);
  border-radius: 4px;
  font-size: 0.85em;
}

.node-index {
  color: var(--text-muted);
  font-weight: 600;
  min-width: 20px;
}

.node-icon {
  font-size: 1em;
}

.node-name {
  color: var(--text-secondary);
}

.nodes-more {
  padding: 6px 10px;
  color: var(--text-muted);
  font-size: 0.85em;
  text-align: center;
  font-style: italic;
}

.preview-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 12px;
}

.tag {
  display: inline-block;
  padding: 3px 8px;
  background: rgba(102, 126, 234, 0.1);
  color: var(--primary-color);
  border-radius: 12px;
  font-size: 0.75em;
  font-weight: 500;
}
</style>
