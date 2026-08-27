<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card budget-card">
      <div class="budget-label">{{ t('restocking.budgetLabel') }}</div>
      <div class="budget-controls">
        <input
          v-model.number="budget"
          type="range"
          min="0"
          max="10000"
          step="50"
          class="budget-slider"
        />
        <div class="budget-readout">{{ currencySymbol }}{{ budget.toLocaleString() }}</div>
      </div>
      <div class="budget-hint">{{ t('restocking.budgetHint') }}</div>
    </div>

    <div v-if="submitSuccess" class="success-banner">
      <strong>{{ t('restocking.orderSuccess') }}</strong>
      <div>{{ successDetail }}</div>
    </div>
    <div v-if="submitError" class="error">{{ submitError }}</div>

    <div v-if="loadingRecommendations" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.summary.totalBudget') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ budget.toLocaleString() }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('restocking.summary.allocated') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ totalAllocated.toLocaleString() }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.summary.remaining') }}</div>
          <div class="stat-value">{{ currencySymbol }}{{ remainingBudget.toLocaleString() }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendedItems') }} ({{ recommendations.length }})</h3>
          <button
            class="place-order-btn"
            :disabled="loadingRecommendations || submitting || recommendations.length === 0"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placingOrder') : t('restocking.placeOrder') }}
          </button>
        </div>

        <div v-if="recommendations.length === 0" class="no-recommendations">
          {{ t('restocking.noRecommendations') }}
        </div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th>{{ t('restocking.table.currentDemand') }}</th>
                <th>{{ t('restocking.table.forecastedDemand') }}</th>
                <th>{{ t('restocking.table.shortfall') }}</th>
                <th>{{ t('restocking.table.unitCost') }}</th>
                <th>{{ t('restocking.table.recommendedQuantity') }}</th>
                <th>{{ t('restocking.table.subtotal') }}</th>
                <th>{{ t('restocking.table.fulfillment') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in recommendations" :key="rec.item_sku">
                <td><strong>{{ rec.item_sku }}</strong></td>
                <td>{{ rec.item_name }}</td>
                <td>
                  <span :class="['badge', rec.trend]">
                    {{ t(`trends.${rec.trend}`) }}
                  </span>
                </td>
                <td>{{ rec.current_demand }}</td>
                <td>{{ rec.forecasted_demand }}</td>
                <td>{{ rec.shortfall }}</td>
                <td>{{ currencySymbol }}{{ rec.unit_cost }}</td>
                <td><strong>{{ rec.recommended_quantity }}</strong></td>
                <td>{{ currencySymbol }}{{ rec.subtotal.toLocaleString() }}</td>
                <td>
                  <span :class="['badge', rec.fully_fulfilled ? 'success' : 'warning']">
                    {{ rec.fully_fulfilled ? t('restocking.fulfillment.full') : t('restocking.fulfillment.partial') }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const budget = ref(3000)
    const recommendations = ref([])
    const totalAllocated = ref(0)
    const remainingBudget = ref(0)
    const loadingRecommendations = ref(false)
    const error = ref(null)

    const submitting = ref(false)
    const submitSuccess = ref(false)
    const submitError = ref(null)
    const successDetail = ref('')

    const loadRecommendations = async () => {
      loadingRecommendations.value = true
      error.value = null
      try {
        const data = await api.getRestockRecommendations(budget.value)
        recommendations.value = data.recommendations
        totalAllocated.value = data.total_allocated
        remainingBudget.value = data.remaining_budget
      } catch (err) {
        error.value = t('restocking.errorLoadingRecommendations')
        console.error(err)
      } finally {
        loadingRecommendations.value = false
      }
    }

    let debounceTimer = null
    watch(budget, () => {
      if (debounceTimer) clearTimeout(debounceTimer)
      debounceTimer = setTimeout(() => {
        loadRecommendations()
      }, 250)
    })

    onBeforeUnmount(() => {
      if (debounceTimer) clearTimeout(debounceTimer)
    })

    const placeOrder = async () => {
      submitting.value = true
      submitError.value = null
      submitSuccess.value = false
      try {
        const payload = {
          budget: budget.value,
          items: recommendations.value.map(r => ({
            item_sku: r.item_sku,
            quantity: r.recommended_quantity
          }))
        }
        const order = await api.submitRestockOrder(payload)
        successDetail.value = t('restocking.orderSuccessDetail', {
          orderId: order.id,
          itemCount: order.items.length,
          totalCost: `${currencySymbol.value}${order.total_cost.toLocaleString()}`,
          leadTime: order.lead_time_days
        })
        submitSuccess.value = true
      } catch (err) {
        submitError.value = t('restocking.errorSubmittingOrder')
        console.error(err)
      } finally {
        submitting.value = false
      }
    }

    onMounted(() => loadRecommendations())

    return {
      t,
      currencySymbol,
      budget,
      recommendations,
      totalAllocated,
      remainingBudget,
      loadingRecommendations,
      error,
      submitting,
      submitSuccess,
      submitError,
      successDetail,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.budget-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.budget-controls {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.budget-slider {
  flex: 1;
  accent-color: #667eea;
}

.budget-readout {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  min-width: 120px;
  text-align: right;
}

.budget-hint {
  font-size: 0.813rem;
  color: #94a3b8;
}

.place-order-btn {
  padding: 0.625rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, opacity 0.2s ease;
  white-space: nowrap;
}

.place-order-btn:hover:not(:disabled) {
  transform: translateY(-2px);
}

.place-order-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.no-recommendations {
  text-align: center;
  padding: 2rem;
  color: #64748b;
  font-style: italic;
}

.success-banner {
  background: #d1fae5;
  color: #065f46;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.25rem;
  font-size: 0.938rem;
}
</style>
