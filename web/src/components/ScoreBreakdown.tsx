import { Badge, Group, Stack, Table, Text, UnstyledButton } from '@mantine/core'
import type { ScoreBreakdown as ScoreBreakdownModel } from '../api/schemas'

type ScoreBreakdownProps = {
  score: ScoreBreakdownModel
  activeCategory: string
  onCategoryFilterChange: (category: string) => void
}

export function ScoreBreakdown({
  score,
  activeCategory,
  onCategoryFilterChange,
}: ScoreBreakdownProps) {
  const categories = sortedEntries(score.by_category)
  const rules = sortedEntries(score.by_rule)
  const bonuses = sortedEntries(score.bonuses)

  return (
    <Stack className="score-breakdown" gap="sm">
      <Group justify="space-between">
        <Text className="surface-title">Score Breakdown</Text>
        <Badge variant="light" color="teal">
          {score.total.toFixed(1)}
        </Badge>
      </Group>
      <BreakdownTable
        title="Categories"
        rows={categories}
        activeKey={activeCategory}
        onRowClick={(category) =>
          onCategoryFilterChange(activeCategory === category ? 'all' : category)
        }
      />
      <BreakdownTable title="Rules" rows={rules} />
      {bonuses.length > 0 ? <BreakdownTable title="Bonuses" rows={bonuses} /> : null}
    </Stack>
  )
}

function BreakdownTable({
  title,
  rows,
  activeKey,
  onRowClick,
}: {
  title: string
  rows: Array<[string, number]>
  activeKey?: string
  onRowClick?: (key: string) => void
}) {
  if (rows.length === 0) {
    return (
      <Stack gap={4}>
        <Text size="sm" fw={700}>
          {title}
        </Text>
        <Text size="sm" c="dimmed">
          None
        </Text>
      </Stack>
    )
  }

  return (
    <Stack gap={4}>
      <Text size="sm" fw={700}>
        {title}
      </Text>
      <Table className="breakdown-table" withTableBorder>
        <Table.Tbody>
          {rows.map(([key, value]) => (
            <Table.Tr key={key} data-selected={activeKey === key || undefined}>
              <Table.Td>
                {onRowClick === undefined ? (
                  key
                ) : (
                  <UnstyledButton
                    className="breakdown-filter"
                    onClick={() => onRowClick(key)}
                  >
                    {key}
                  </UnstyledButton>
                )}
              </Table.Td>
              <Table.Td className="breakdown-value">{value.toFixed(1)}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  )
}

function sortedEntries(values: Record<string, number>): Array<[string, number]> {
  return Object.entries(values).sort((left, right) => {
    const byValue = Math.abs(right[1]) - Math.abs(left[1])
    return byValue === 0 ? left[0].localeCompare(right[0]) : byValue
  })
}
