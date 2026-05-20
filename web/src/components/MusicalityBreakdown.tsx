import { Badge, Group, Stack, Table, Text } from '@mantine/core'
import type { MusicalityBreakdown as MusicalityBreakdownModel } from '../api/schemas'

type MusicalityBreakdownProps = {
  musicality: MusicalityBreakdownModel | null | undefined
}

export function MusicalityBreakdown({ musicality }: MusicalityBreakdownProps) {
  if (musicality === null || musicality === undefined) {
    return null
  }

  return (
    <Stack className="musicality-breakdown" gap="sm">
      <Group justify="space-between">
        <Text className="surface-title">Musicality</Text>
        <Badge variant="light" color="indigo">
          {musicality.total.toFixed(1)}
        </Badge>
      </Group>
      <Table className="breakdown-table" withTableBorder>
        <Table.Tbody>
          {musicality.metrics.map((metric) => (
            <Table.Tr key={metric.key}>
              <Table.Td>
                <Text size="sm">{metric.label}</Text>
                <Text size="xs" c="dimmed">
                  raw {metric.raw_value.toFixed(2)}
                </Text>
              </Table.Td>
              <Table.Td className="breakdown-value">
                {(metric.normalized_value * 100).toFixed(0)}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  )
}
