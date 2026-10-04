"use client";

import { useState } from "react";
import { Check, Truck, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import {
  useAcceptOrder,
  useRejectOrder,
  useShipOrder,
} from "@/hooks/use-admin-orders";
import type { OrderReadAdmin } from "@/lib/api-types";

interface Props {
  order: OrderReadAdmin;
}

export function OrderActions({ order }: Props) {
  const accept = useAcceptOrder();
  const reject = useRejectOrder();
  const ship = useShipOrder();

  const [acceptOpen, setAcceptOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);

  const [acceptNotes, setAcceptNotes] = useState("");
  const [rejectReason, setRejectReason] = useState("");

  const canAccept = order.status === "pending";
  const canReject =
    order.status === "pending" || order.status === "confirmed";
  const canShip = order.status === "confirmed";

  const handleAccept = () => {
    accept.mutate(
      {
        orderId: order.id,
        payload: { notes: acceptNotes.trim() || null },
      },
      {
        onSuccess: () => {
          setAcceptOpen(false);
          setAcceptNotes("");
        },
      },
    );
  };

  const handleReject = () => {
    if (rejectReason.trim().length < 3) return;
    reject.mutate(
      { orderId: order.id, payload: { reason: rejectReason.trim() } },
      {
        onSuccess: () => {
          setRejectOpen(false);
          setRejectReason("");
        },
      },
    );
  };

  const handleShip = () => {
    if (!confirm("Mark this order as shipped?")) return;
    ship.mutate(order.id);
  };

  return (
    <>
      <div className="flex flex-wrap gap-2">
        {canAccept && (
          <Button
            size="sm"
            onClick={() => setAcceptOpen(true)}
            disabled={accept.isPending}
          >
            <Check className="mr-1 h-4 w-4" />
            Accept
          </Button>
        )}
        {canShip && (
          <Button
            size="sm"
            variant="secondary"
            onClick={handleShip}
            disabled={ship.isPending}
          >
            <Truck className="mr-1 h-4 w-4" />
            {ship.isPending ? "Shipping…" : "Mark shipped"}
          </Button>
        )}
        {canReject && (
          <Button
            size="sm"
            variant="outline"
            className="text-destructive hover:text-destructive"
            onClick={() => setRejectOpen(true)}
            disabled={reject.isPending}
          >
            <X className="mr-1 h-4 w-4" />
            Reject
          </Button>
        )}
        {!canAccept && !canShip && !canReject && (
          <span className="text-xs text-muted-foreground">
            No actions available
          </span>
        )}
      </div>

      {/* Accept dialog */}
      <Dialog open={acceptOpen} onOpenChange={setAcceptOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Accept order #{order.id}?</DialogTitle>
            <DialogDescription>
              This marks the order as CONFIRMED. You can add internal notes.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="accept-notes">Notes (optional)</Label>
            <Textarea
              id="accept-notes"
              value={acceptNotes}
              onChange={(e) => setAcceptNotes(e.target.value)}
              placeholder="e.g., Payment verified, ready to ship"
              rows={3}
              disabled={accept.isPending}
            />
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setAcceptOpen(false)}
              disabled={accept.isPending}
            >
              Cancel
            </Button>
            <Button onClick={handleAccept} disabled={accept.isPending}>
              {accept.isPending ? "Accepting…" : "Accept order"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reject dialog */}
      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject order #{order.id}?</DialogTitle>
            <DialogDescription>
              The customer will see your reason. The order becomes REJECTED.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-2">
            <Label htmlFor="reject-reason">
              Reason <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="reject-reason"
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g., Item out of stock, invalid shipping address"
              rows={3}
              disabled={reject.isPending}
            />
            <p className="text-xs text-muted-foreground">
              Minimum 3 characters.
            </p>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setRejectOpen(false)}
              disabled={reject.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={rejectReason.trim().length < 3 || reject.isPending}
            >
              {reject.isPending ? "Rejecting…" : "Reject order"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
